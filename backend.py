from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import requests

app = FastAPI()


# ---------- DB ---------- #

def get_conn():
    return psycopg2.connect(
        dbname="movie_db",
        user="postgres",
        password="Apex@2417",
        host="localhost",
        port="5432"
    )


# ---------- SCHEMAS ---------- #

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class MovieCreate(BaseModel):
    title: str
    release_year: int | None = None
    runtime: int | None = None
    description: str | None = None
    poster_url: str | None = None


class TMDBMovieCreate(BaseModel):
    tmdb_id: int


class WatchlistCreate(BaseModel):
    user_id: int
    movie_id: int
    watch_status: str


class WatchlistUpdate(BaseModel):
    watch_status: str | None = None
    rating: int | None = None
    review: str | None = None
    liked: bool | None = None


# ---------- ROOT ---------- #

@app.get("/")
def root():
    return {"message": "API running"}


# ---------- USERS ---------- #

@app.post("/users")
def create_user(data: UserCreate):
    hashed_pw = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())

    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (data.username, data.email, hashed_pw.decode())
        )
        conn.commit()
        user_id = cursor.fetchone()["id"]
    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        cursor.close()
        conn.close()

    return {"user_id": user_id}


# ---------- MOVIES ---------- #

@app.post("/movies")
def add_movie(data: MovieCreate):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            """
            INSERT INTO movies (title, release_year, runtime, description_movie, poster_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data.title,
                data.release_year,
                data.runtime,
                data.description,
                data.poster_url
            )
        )
        conn.commit()
        movie_id = cursor.fetchone()["id"]
    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        cursor.close()
        conn.close()

    return {"movie_id": movie_id}


@app.post("/movies/from-tmdb")
def add_movie_from_tmdb(data: TMDBMovieCreate):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # check if exists
        cursor.execute(
            "SELECT id FROM movies WHERE tmdb_id = %s",
            (data.tmdb_id,)
        )
        existing = cursor.fetchone()

        if existing:
            return {"movie_id": existing["id"], "status": "exists"}

        # fetch from tmdb
        url = f"https://api.themoviedb.org/3/movie/{data.tmdb_id}"
        params = {"api_key": TMDB_API_KEY}

        try:
          res = requests.get(url, params=params, timeout=5)
          res.raise_for_status()
          movie = res.json()
        except requests.exceptions.RequestException:
            raise HTTPException(500, "TMDb request failed")

        if "id" not in movie:
            raise HTTPException(404, "TMDb movie not found")

        title = movie.get("title")
        release_year = movie.get("release_date", "")[:4] if movie.get("release_date") else None
        runtime = movie.get("runtime")
        description = movie.get("overview")
        poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None

        cursor.execute(
            """
            INSERT INTO movies (title, release_year, runtime, description_movie, poster_url, tmdb_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (title, release_year, runtime, description, poster_url, data.tmdb_id)
        )

        conn.commit()
        movie_id = cursor.fetchone()["id"]

    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        cursor.close()
        conn.close()

    return {"movie_id": movie_id, "status": "created"}


@app.get("/movies")
def get_movies():
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM movies ORDER BY id DESC")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"data": data}


@app.get("/movies/{movie_id}")
def get_movie(movie_id: int):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    movie = cursor.fetchone()

    cursor.close()
    conn.close()

    if not movie:
        raise HTTPException(404, "Movie not found")

    return movie


# ---------- WATCHLIST ---------- #

@app.post("/watchlist")
def add_to_watchlist(data: WatchlistCreate):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            """
            INSERT INTO watchlist (user_id, movie_id, watch_status)
            VALUES (%s, %s, %s)
            """,
            (data.user_id, data.movie_id, data.watch_status)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        cursor.close()
        conn.close()

    return {"message": "added"}


@app.patch("/watchlist/{id}")
def update_watchlist(id: int, data: WatchlistUpdate):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # only update provided fields
        fields = []
        values = []

        if data.watch_status is not None:
            fields.append("watch_status = %s")
            values.append(data.watch_status)

        if data.rating is not None:
            fields.append("rating = %s")
            values.append(data.rating)

        if data.review is not None:
            fields.append("review = %s")
            values.append(data.review)

        if data.liked is not None:
            fields.append("liked = %s")
            values.append(data.liked)

        if not fields:
            raise HTTPException(400, "No fields to update")

        query = f"""
            UPDATE watchlist
            SET {', '.join(fields)}
            WHERE id = %s
            RETURNING id
        """

        values.append(id)

        cursor.execute(query, tuple(values))
        updated = cursor.fetchone()

        if not updated:
            raise HTTPException(404, "Watchlist item not found")

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        cursor.close()
        conn.close()

    return {"message": "updated"}


@app.get("/watchlist/{user_id}")
def get_watchlist(user_id: int):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT w.*, m.title
        FROM watchlist w
        JOIN movies m ON w.movie_id = m.id
        WHERE w.user_id = %s
        ORDER BY w.added_at DESC
        """,
        (user_id,)
    )
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"data": data}


# ---------- STATS ---------- #

@app.get("/stats/{user_id}")
def get_stats(user_id: int):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        "SELECT * FROM user_stats WHERE user_id = %s",
        (user_id,)
    )
    stats = cursor.fetchone()

    cursor.close()
    conn.close()

    return stats if stats else {}


@app.get("/movie-ratings")
def movie_ratings():
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM movie_ratings ORDER BY avg_rating DESC")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"data": data}


# ---------- TMDB SEARCH ---------- #

TMDB_API_KEY = "12fc8cf89b5ae4193aa2d86a52aa9b26"


@app.get("/search-movies")
def search_movies(q: str):
    url = "https://api.themoviedb.org/3/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": q
    }

    try:
      res = requests.get(url, params=params, timeout=5)
      res.raise_for_status()
      data = res.json()
    except requests.exceptions.RequestException:
        raise HTTPException(500, "TMDb request failed")

    results = []

    for movie in data.get("results", [])[:10]:
        results.append({
            "tmdb_id": movie["id"],
            "title": movie["title"],
            "release_year": movie["release_date"][:4] if movie.get("release_date") else None,
            "overview": movie.get("overview"),
            "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None
        })

    return {"data": results}

class AddFromSearch(BaseModel):
    user_id: int
    tmdb_id: int
    watch_status: str = "want"


@app.post("/watchlist/from-tmdb")
def add_from_tmdb(data: AddFromSearch):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. check if movie exists
        cursor.execute(
            "SELECT id FROM movies WHERE tmdb_id = %s",
            (data.tmdb_id,)
        )
        existing = cursor.fetchone()

        if existing:
            movie_id = existing["id"]
        else:
            # 2. fetch from tmdb
            url = f"https://api.themoviedb.org/3/movie/{data.tmdb_id}"
            params = {"api_key": TMDB_API_KEY}

            try:
                res = requests.get(url, params=params, timeout=5)
                res.raise_for_status()
                movie = res.json()
            except requests.exceptions.RequestException:
                raise HTTPException(500, "TMDb request failed")

            title = movie.get("title")
            release_year = movie.get("release_date")[:4] if movie.get("release_date") else None
            runtime = movie.get("runtime")
            description = movie.get("overview")
            poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None

            cursor.execute(
                """
                INSERT INTO movies (title, release_year, runtime, description_movie, poster_url, tmdb_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (title, release_year, runtime, description, poster_url, data.tmdb_id)
            )

            movie_id = cursor.fetchone()["id"]

        # 3. add to watchlist
        cursor.execute(
            """
            INSERT INTO watchlist (user_id, movie_id, watch_status)
            VALUES (%s, %s, %s)
            """,
            (data.user_id, movie_id, data.watch_status)
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        cursor.close()
        conn.close()

    return {
        "movie_id": movie_id,
        "status": "added to watchlist"
    }