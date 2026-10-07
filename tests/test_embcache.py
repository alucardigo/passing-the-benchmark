"""Cache de embeddings: texto já visto não volta ao encoder, nem entre processos."""
import numpy as np

from ptguard.embcache import CachedEmbedder


class Counting:
    def __init__(self):
        self.seen = []

    def __call__(self, texts):
        self.seen.extend(texts)
        return np.array([[len(t), 1.0] for t in texts], dtype=np.float32)


def test_only_new_texts_reach_the_encoder_and_order_is_kept(tmp_path):
    enc = Counting()
    cached = CachedEmbedder(enc, tmp_path / "e5.npz")
    first = cached(["aa", "b"])
    second = cached(["b", "ccc", "aa"])
    assert enc.seen == ["aa", "b", "ccc"]
    assert second[:, 0].tolist() == [1.0, 3.0, 2.0]
    assert np.array_equal(first[0], second[2])


def test_cache_survives_a_new_process(tmp_path):
    CachedEmbedder(Counting(), tmp_path / "e5.npz")(["x", "yy"])
    enc = Counting()
    out = CachedEmbedder(enc, tmp_path / "e5.npz")(["yy", "x"])
    assert enc.seen == [] and out[:, 0].tolist() == [2.0, 1.0]
