import streamlit as st
import pandas as pd
import joblib
import difflib
import requests
import re
import time

# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------
st.set_page_config(
    page_title="🎬 Movie Recommender System",
    page_icon="🎬",
    layout="wide"
)

# ------------------------------------------------------------
# BACKGROUND IMAGE
# ------------------------------------------------------------
# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------
st.set_page_config(
    page_title="🎬 Movie Recommender System",
    page_icon="🎬",
    layout="wide"
)

# ------------------------------------------------------------
# BACKGROUND IMAGE
# ------------------------------------------------------------
def add_bg_with_overlay():
    import base64

    # Read the local image file and encode it as Base64
    with open("background.png", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    # Apply as background with dark overlay for readability
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(
                rgba(0, 0, 0, 0.75),
                rgba(0, 0, 0, 0.75)
            ), url("data:image/png;base64,{encoded_string}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
            color: white !important;
        }}
        .stMetric-label, .stMetric-value {{
            color: white !important;
        }}
        .stRadio label {{
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 👇 Call it immediately after defining it
add_bg_with_overlay()



# ------------------------------------------------------------
# LOAD PRECOMPUTED DATA FROM PICKLE
# ------------------------------------------------------------
@st.cache_resource
def load_data():
    """Load precomputed movie data from .pkl file."""
    try:
        data = joblib.load("movie_data.pkl")
        movies = data["movies"]
        ratings = data["ratings"]
        cosine_sim_df = data["cosine_sim_df"]

        # Ensure lowercase column exists
        if "title_lower" not in movies.columns:
            movies["title_lower"] = movies["title"].str.lower()

        return movies, ratings, cosine_sim_df

    except FileNotFoundError:
        st.error("❌ File 'movie_data.pkl' not found. Please place it in the same folder as app.py.")
        st.stop()

# ------------------------------------------------------------
# TMDB POSTER FETCH FUNCTION (with caching + cleaning)
# ------------------------------------------------------------
TMDB_API_KEY = "bad1ca30f718a1a0e7f72b90cb8c72b3"  # 🔑 Replace with your actual TMDB key

@st.cache_data(show_spinner=False)
def get_movie_poster(title):
    """Fetch and cache movie poster URL from TMDB API."""
    def clean_title(title):
        # Remove year or parentheses for better matching
        return re.sub(r"\(\d{4}\)", "", title).strip()

    base_url = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": clean_title(title)}

    try:
        response = requests.get(base_url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                poster_path = data["results"][0].get("poster_path")
                if poster_path:
                    return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        pass

    return None  # No result found

# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def find_best_match(query, movies, ratings):
    """Find the closest movie title from user input (partial or fuzzy)."""
    query = query.strip().lower()
    if not query:
        return None

    # Direct substring match first
    substr = movies[movies["title_lower"].str.contains(query, na=False, regex=False)]
    if not substr.empty:
        counts = ratings.groupby("movieId").size().rename("rating_count")
        merged = substr.merge(counts, on="movieId", how="left").fillna(0)
        merged = merged.sort_values(by="rating_count", ascending=False)
        return merged.iloc[0]["title"]

    # If not found, use fuzzy matching
    all_titles = movies["title"].tolist()
    close = difflib.get_close_matches(query, all_titles, n=1, cutoff=0.5)
    return close[0] if close else None


def get_recommendations(movie_title, movies, cosine_sim_df, n=10):
    """Get top-N similar movies using precomputed cosine similarity."""
    matches = movies[movies["title"] == movie_title]
    if matches.empty:
        return None, f"❌ Movie '{movie_title}' not found in dataset."

    movie_id = int(matches["movieId"].values[0])
    if movie_id not in cosine_sim_df.index:
        return None, f"⚠️ No rating data available for '{movie_title}'."

    sim_scores = cosine_sim_df[movie_id].sort_values(ascending=False)
    sim_scores = sim_scores.drop(movie_id, errors="ignore")
    top_ids = sim_scores.head(n).index.tolist()

    recommended = movies[movies["movieId"].isin(top_ids)][["title", "genres"]]
    return recommended, None

# ------------------------------------------------------------
# MAIN APP
# ------------------------------------------------------------
def main():
    st.title("🎬 Movie Recommendation System")
    st.markdown("**Discover movies similar to your favorites using collaborative filtering!**")
    st.divider()

    # Load data
    with st.spinner("🔄 Loading precomputed movie data..."):
        movies, ratings, cosine_sim_df = load_data()

    # Display basic stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📽️ Total Movies", f"{len(movies):,}")
    with col2:
        st.metric("⭐ Total Ratings", f"{len(ratings):,}")
    with col3:
        st.metric("👥 Total Users", f"{ratings['userId'].nunique():,}")

    st.divider()

    # Search section
    st.subheader("🔍 Find Your Movie")

    input_method = st.radio(
        "Choose input method:",
        ["Type movie name", "Select from dropdown"],
        horizontal=True
    )

    if input_method == "Type movie name":
        movie_input = st.text_input(
            "Enter part of a movie title:",
            placeholder="e.g., Avatar, Inception, Avengers..."
        )
    else:
        movie_list = [""] + sorted(movies["title"].tolist())
        movie_input = st.selectbox("Select a movie:", movie_list)

    n_recommendations = st.slider(
        "Number of recommendations:",
        min_value=5, max_value=20, value=10, step=1
    )

    # Search button
    if st.button("🎯 Get Recommendations", type="primary"):
        if not movie_input:
            st.warning("⚠️ Please enter or select a movie title!")
        else:
            with st.spinner("🔍 Finding similar movies..."):
                best_match = (
                    find_best_match(movie_input, movies, ratings)
                    if input_method == "Type movie name"
                    else movie_input
                )

                if best_match:
                    st.success(f"✅ **Matched Movie:** {best_match}")

                    recs, error = get_recommendations(best_match, movies, cosine_sim_df, n_recommendations)
                    if error:
                        st.error(error)
                    else:
                        st.divider()
                        st.subheader(f"🎥 Top {n_recommendations} Similar Movies")

                        for idx, (_, row) in enumerate(recs.iterrows(), 1):
                            with st.container():
                                col1, col2 = st.columns([1, 5])

                                poster_url = get_movie_poster(row["title"]) or "https://via.placeholder.com/300x450?text=No+Image"

                                # Optional delay to respect TMDB rate limits
                                time.sleep(0.1)

                                with col1:
                                    st.image(poster_url, width='stretch')

                                with col2:
                                    st.markdown(f"### {idx}. **{row['title']}**")
                                    st.caption(f"🏷️ {row['genres']}")
                            st.divider()
                else:
                    st.error("❌ No close matches found. Try another title or use the dropdown!")

    st.divider()
    st.caption("💡 **Tip:** This version caches poster images for faster, smoother recommendations.")

    st.markdown(
    """
    <div style='text-align: center; font-size: 1.1em; color: #f5f5f5; margin-top: 2em;'>
        🎬 <em>Smarter recommendations. Seamless experience.</em>
    </div>
    """,
    unsafe_allow_html=True
)



# ------------------------------------------------------------
if __name__ == "__main__":
    main()
