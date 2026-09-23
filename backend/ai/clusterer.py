import numpy as np
from sklearn.cluster import AgglomerativeClustering
from typing import List, Optional
from backend.config import DEFAULT_COSINE_THRESHOLD


class FaceClusterer:
    """
    Two-Stage Safe Cosine Distance Clustering Engine for Face Embeddings.

    Stage 1: Agglomerative Clustering using 'average' linkage (mean pairwise distance).
    Stage 2: Safe Centroid Merger — merges candidate clusters only when centroid distance
             is strictly within identity limits (≤ 0.50), preventing over-merging & domino collapses.

    Clamps distance thresholds to safe bounds for SFace 512D embeddings (0.35 to 0.52).
    """

    def __init__(self, distance_threshold: float = DEFAULT_COSINE_THRESHOLD):
        self.distance_threshold = distance_threshold

    def cluster(self, embeddings: List[np.ndarray], distance_threshold: Optional[float] = None) -> List[int]:
        """
        Cluster a list of 512D normalized embedding vectors.

        Safe Threshold limits:
          0.38 = Strict (near-identical faces only)
          0.45 = Balanced frontal (default for events)
          0.48 = Pose-tolerant (handles 3/4 angles & pose variations)
          0.52 = Maximum multi-angle threshold (prevents merging distinct identities)
        """
        if not embeddings:
            return []

        # Filter out invalid or non-numpy embedding arrays
        valid_embeddings = [emb.flatten().astype(np.float32) for emb in embeddings if isinstance(emb, np.ndarray) and emb.size > 0]
        if not valid_embeddings:
            return []

        # Find target feature dimension (most common dimension, e.g. 512D)
        shapes = [emb.shape[0] for emb in valid_embeddings]
        target_dim = max(set(shapes), key=shapes.count)

        # Keep only embeddings matching the primary target dimension
        filtered_embeddings = [emb for emb in valid_embeddings if emb.shape[0] == target_dim]

        if not filtered_embeddings:
            return []

        if len(filtered_embeddings) == 1:
            return [0]

        raw_thresh = distance_threshold if distance_threshold is not None else self.distance_threshold
        # HARD CAP: Clamp threshold to safe bounds for SFace 512D (0.35 to 0.52).
        # Anything above 0.52 causes distinct people to merge together.
        thresh = float(np.clip(raw_thresh, 0.35, 0.52))

        X = np.vstack(filtered_embeddings).astype(np.float32)

        # L2 normalize all embeddings (ensure unit vectors for cosine math)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        X = X / norms

        # Cosine Distance Matrix: D[i,j] = 1 - dot(X[i], X[j])
        similarity_matrix = np.clip(np.dot(X, X.T), -1.0, 1.0)
        distance_matrix = np.clip(1.0 - similarity_matrix, 0.0, 2.0)

        # STAGE 1: Agglomerative Clustering with 'average' linkage
        clustering_model = AgglomerativeClustering(
            n_clusters=None,
            metric='precomputed',
            linkage='average',
            distance_threshold=thresh
        )

        initial_labels = clustering_model.fit_predict(distance_matrix).tolist()

        # STAGE 2: Post-Processing Centroid Merge Pass
        # Compute normalized 512D centroid vector for each candidate cluster
        cluster_vectors = {}
        for idx, lbl in enumerate(initial_labels):
            cluster_vectors.setdefault(lbl, []).append(X[idx])

        centroids = {}
        for lbl, vecs in cluster_vectors.items():
            c_mean = np.mean(vecs, axis=0)
            c_norm = np.linalg.norm(c_mean)
            centroids[lbl] = c_mean / c_norm if c_norm > 0 else c_mean

        # Safe centroid merger limit: max 0.50 distance
        safe_centroid_thresh = min(0.50, thresh * 1.02)

        parent = {lbl: lbl for lbl in centroids.keys()}

        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_j] = root_i

        lbl_keys = list(centroids.keys())
        for i in range(len(lbl_keys)):
            k1 = lbl_keys[i]
            for j in range(i + 1, len(lbl_keys)):
                k2 = lbl_keys[j]
                if find(k1) != find(k2):
                    # Cosine distance between cluster centroids
                    sim = float(np.clip(np.dot(centroids[k1], centroids[k2]), -1.0, 1.0))
                    c_dist = 1.0 - sim
                    if c_dist <= safe_centroid_thresh:
                        union(k1, k2)

        # Map final cluster labels
        final_raw_labels = [find(lbl) for lbl in initial_labels]

        # Compact label indices (0, 1, 2, ...)
        unique_labels = {lbl: idx for idx, lbl in enumerate(sorted(set(final_raw_labels)))}
        compacted = [unique_labels[lbl] for lbl in final_raw_labels]

        return compacted
