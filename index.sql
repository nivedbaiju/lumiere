CREATE INDEX idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX idx_watchlist_status ON watchlist(watch_status);

CREATE INDEX idx_movies_title ON movies(title);

CREATE INDEX idx_movie_genres_movie_id ON movie_genres(movie_id);
CREATE INDEX idx_movie_genres_genre_id ON movie_genres(genre_id);

CREATE INDEX idx_collections_user_id ON collections(user_id);

CREATE INDEX idx_collection_movies_collection_id ON collection_movies(collection_id);
CREATE INDEX idx_collection_movies_movie_id ON collection_movies(movie_id);

CREATE INDEX idx_watchlist_history_watchlist_id ON watchlist_history(watchlist_id);