CREATE VIEW user_stats AS
SELECT
    w.user_id,
    COUNT(*) FILTER (WHERE w.watch_status = 'watched') AS total_watched,
    COUNT(*) FILTER (WHERE w.watch_status = 'watching') AS currently_watching,
    COUNT(*) FILTER (WHERE w.watch_status = 'want') AS want_to_watch,
    AVG(w.rating) FILTER (WHERE w.rating IS NOT NULL) AS avg_rating,
    SUM(m.runtime) FILTER (WHERE w.watch_status = 'watched') AS total_runtime
FROM watchlist w
JOIN movies m ON w.movie_id = m.id
GROUP BY w.user_id;

CREATE VIEW genre_stats AS
SELECT
    w.user_id,
    g.genre_name,
    COUNT(*) AS total_movies,
    AVG(w.rating) FILTER (WHERE w.rating IS NOT NULL) AS avg_rating
FROM watchlist w
JOIN movies m ON w.movie_id = m.id
JOIN movie_genres mg ON m.id = mg.movie_id
JOIN genres g ON mg.genre_id = g.id
WHERE w.watch_status = 'watched'
GROUP BY w.user_id, g.genre_name;

CREATE VIEW yearly_stats AS
SELECT
    w.user_id,
    m.release_year,
    COUNT(*) AS movies_watched,
    AVG(w.rating) FILTER (WHERE w.rating IS NOT NULL) AS avg_rating
FROM watchlist w
JOIN movies m ON w.movie_id = m.id
WHERE w.watch_status = 'watched'
GROUP BY w.user_id, m.release_year
ORDER BY m.release_year;

CREATE VIEW movie_ratings AS
SELECT
    w.movie_id,
    m.title,
    AVG(w.rating) AS avg_rating,
    COUNT(w.rating) AS total_ratings
FROM watchlist w
JOIN movies m ON w.movie_id = m.id
WHERE w.rating IS NOT NULL
GROUP BY w.movie_id, m.title;