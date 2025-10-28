import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import difflib
import joblib
import os

# ------------------------------------------------------------
# STEP 1: Load Data
# ------------------------------------------------------------
# Use local relative paths — works for both GitHub and Colab
movies_path = os.path.join("data", "movies.csv")
ratings_path = os.path.join("data", "ratings.csv")

print("📂 Loading datasets...")
movies = pd.read_csv(movies_path)
ratings = pd.read_csv(ratings_path)

print(f"✅ Movies loaded: {movies.shape}")
print(f"✅ Ratings loaded: {ratings.shape}")

# ------------------------------------------------------------
# STEP 2: Build Item-Item Similarity Matrix
# ------------------------------------------------------------
print("\n⚙️ Building cosine similarity matrix (this may take a while)...")

# Pivot ratings to get movieId × userId matrix
rating_matrix = ratings.pivot_table(index="movieId", columns="userId", values="rating").fillna(0)

# Compute cosine similarity between movies
cosine_sim = cosine_similarity(rating_matrix)
cosine_sim_df = pd.DataFrame(cosine_sim, index=rating_matrix.index, columns=rating_matrix.index)

# Add lowercase title for better search
movies["title_lower"] = movies["title"].str.lower()

print("✅ Cosine similarity matrix created.")
print(f"   → Matrix shape: {cosine_sim_df.shape}")

# ------------------------------------------------------------
# STEP 3: Optional Testing – Try a Few Recommendations
# ------------------------------------------------------------
def find_best_match(query):
    """Find the closest movie title from user input (partial or fuzzy)."""
    query = query.strip().lower()
    if not query:
        return None

    substr = movies[movies["title_lower"].str.contains(query, na=False)]
    if not substr.empty:
        counts = ratings.groupby("movieId").size().rename("rating_count")
        merged = substr.merge(counts, on="movieId", how="left").fillna(0)
        merged = merged.sort_values(by="rating_count", ascending=False)
        return merged.iloc[0]["title"]

    all_titles = movies["title"].tolist()
    close = difflib.get_close_matches(query, all_titles, n=1, cutoff=0.5)
    return close[0] if close else None


def recommend_movies(movie_title, n=10):
    """Recommend similar movies using cosine similarity."""
    matches = movies[movies["title"] == movie_title]
    if matches.empty:
        print(f"❌ Movie '{movie_title}' not found in dataset.")
        return

    movie_id = int(matches["movieId"].values[0])
    if movie_id not in cosine_sim_df.index:
        print(f"⚠️ No rating data available for '{movie_title}'.")
        return

    sim_scores = cosine_sim_df[movie_id].sort_values(ascending=False)
    sim_scores = sim_scores.drop(movie_id, errors="ignore")
    top_ids = sim_scores.head(n).index.tolist()

    recommended = movies[movies["movieId"].isin(top_ids)][["title", "genres"]]
    print(f"\n🎥 Top {n} movies similar to '{movie_title}':\n")
    for i, row in recommended.iterrows():
        print(f"{i+1}. {row['title']}  ({row['genres']})")


# ------------------------------------------------------------
# STEP 4: Save Precomputed Data to Pickle
# ------------------------------------------------------------
print("\n💾 Saving precomputed data to movie_data.pkl...")
data = {
    "movies": movies,
    "ratings": ratings,
    "cosine_sim_df": cosine_sim_df
}

output_path = "movie_data.pkl"
joblib.dump(data, output_path)
print(f"✅ Pickle file saved successfully at: {output_path}")

# ------------------------------------------------------------
# STEP 5: Optional Interactive Run (for testing only)
# ------------------------------------------------------------
if __name__ == "__main__":
    query = input("\n🔍 Enter part of a movie title to test recommendations: ").strip()
    best_match = find_best_match(query)

    if best_match:
        print(f"\n✅ Closest match found: {best_match}")
        recommend_movies(best_match, n=10)
    else:
        print("❌ No close matches found. Try another title.")
