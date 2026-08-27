# training/eval_threshold.py
import pickle, numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# load
questions = pickle.load(open("../model/questions_emb.pkl","rb"))
answers = pickle.load(open("../model/answers_emb.pkl","rb"))
emb = np.load("../model/embeddings.npy")
nn = pickle.load(open("../model/nn_emb.pkl","rb"))
val_q, val_a = pickle.load(open("../model/validation_emb.pkl","rb"))

model = SentenceTransformer("all-MiniLM-L6-v2")
val_emb = model.encode(val_q, convert_to_numpy=True, normalize_embeddings=True).astype("float32")

# for each val sample, get nearest neighbor score
distances, idxs = nn.kneighbors(val_emb, n_neighbors=1)
# metric='cosine' => distances are cosine distances (0 identical, 1 different)
scores = 1 - distances.flatten()  # convert to cosine similarity

# compute accuracy per threshold
thresholds = np.linspace(0.35, 0.85, 21)
best = (0,0)
for t in thresholds:
    correct = 0
    for i, sim in enumerate(scores):
        if sim >= t:
            # predicted answer index
            pred_idx = idxs[i][0]
            # exact-match check between val_q's gold and predicted answer? Instead use semantic match: check if predicted answer matches val_a
            if answers[pred_idx].strip().lower() == val_a[i].strip().lower():
                correct += 1
    acc = correct / len(val_q)
    print(f"threshold {t:.2f} -> accuracy {acc:.3f} ({correct}/{len(val_q)})")
    if acc > best[0]:
        best = (acc, t)
print("Best threshold:", best)