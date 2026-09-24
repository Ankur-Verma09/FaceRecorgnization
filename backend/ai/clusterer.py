import numpy as np
from sklearn.cluster import AgglomerativeClustering
from collections import Counter
from backend.config import (
    DEFAULT_COSINE_THRESHOLD, TIGHT_CLUSTER_THRESHOLD,
    MAX_CENTROID_MERGE_THRESHOLD, MIN_PAIRWISE_SAFETY_THRESHOLD
)

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i):
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1

class FaceClusterer:
    """
    Adaptive Multi-Pass Face Clustering.
    Pass 1: Tight Micro-Clusters using average linkage Agglomerative Clustering.
    Pass 2: Adaptive Centroid Merge using Union-Find and a minimum pairwise safety check.
    """
    def __init__(self, distance_threshold=DEFAULT_COSINE_THRESHOLD):
        self.distance_threshold = distance_threshold

    def cluster(self, embeddings_list, distance_threshold=None):
        """
        Clusters a list of embeddings.
        Returns a list of cluster labels of the same length as the input list.
        Invalid embeddings or those with incorrect dimensions are labeled as -1.
        """
        if not embeddings_list:
            return []
            
        threshold = distance_threshold if distance_threshold is not None else self.distance_threshold
            
        # Filter valid embeddings
        valid_embs = []
        valid_indices = []
        for i, emb in enumerate(embeddings_list):
            if isinstance(emb, np.ndarray) and emb.size > 0:
                valid_embs.append(emb.flatten())
                valid_indices.append(i)
                
        if not valid_embs:
            return [-1] * len(embeddings_list)
            
        if len(valid_embs) == 1:
            res = [-1] * len(embeddings_list)
            res[valid_indices[0]] = 0
            return res
            
        # Ensure same dimension
        dims = [emb.shape[0] for emb in valid_embs]
        most_common_dim = Counter(dims).most_common(1)[0][0]
        
        filtered_embs = []
        idx_map = []
        for orig_idx, emb in zip(valid_indices, valid_embs):
            if emb.shape[0] == most_common_dim:
                filtered_embs.append(emb)
                idx_map.append(orig_idx)
        
        if not filtered_embs:
            return [-1] * len(embeddings_list)
            
        if len(filtered_embs) == 1:
            res = [-1] * len(embeddings_list)
            res[idx_map[0]] = 0
            return res

        X = np.array(filtered_embs)
        
        # L2 normalize
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1
        X_norm = X / norms
        
        # Cosine distance matrix
        D = 1.0 - np.dot(X_norm, X_norm.T)
        D = np.clip(D, 0.0, 2.0)
        
        # Pass 1: Tight Micro-Clusters
        agg_cluster = AgglomerativeClustering(
            n_clusters=None,
            metric='precomputed',
            linkage='average',
            distance_threshold=TIGHT_CLUSTER_THRESHOLD
        )
        micro_labels = agg_cluster.fit_predict(D)
        
        # Pass 2: Adaptive Centroid Merge
        num_micro = len(set(micro_labels))
        micro_indices = {i: [] for i in range(num_micro)}
        for idx, label in enumerate(micro_labels):
            micro_indices[label].append(idx)
            
        centroids = []
        for i in range(num_micro):
            cluster_embs = X_norm[micro_indices[i]]
            c = np.mean(cluster_embs, axis=0)
            c_norm = np.linalg.norm(c)
            if c_norm > 0:
                c = c / c_norm
            centroids.append(c)
        centroids = np.array(centroids)
        
        centroid_thresh = min(threshold, MAX_CENTROID_MERGE_THRESHOLD)
        
        uf = UnionFind(num_micro)
        for i in range(num_micro):
            for j in range(i + 1, num_micro):
                dist = 1.0 - np.dot(centroids[i], centroids[j])
                dist = max(0.0, min(dist, 2.0))
                
                if dist <= centroid_thresh:
                    # Safety check: min pairwise distance between cluster members
                    sub_D = D[np.ix_(micro_indices[i], micro_indices[j])]
                    min_pairwise = np.min(sub_D)
                    if min_pairwise <= MIN_PAIRWISE_SAFETY_THRESHOLD:
                        uf.union(i, j)
                        
        final_labels = [uf.find(i) for i in range(num_micro)]
        
        # Compact labels
        unique_labels = list(set(final_labels))
        unique_labels.sort()
        label_map = {old: new for new, old in enumerate(unique_labels)}
        
        compact_labels = [label_map[final_labels[micro_labels[i]]] for i in range(len(X_norm))]
        
        # Map back to original indices
        result = [-1] * len(embeddings_list)
        for filtered_idx, orig_idx in enumerate(idx_map):
            result[orig_idx] = compact_labels[filtered_idx]
            
        return result
