CREATE OR REPLACE FUNCTION log_watchlist_status_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO watchlist_history (watchlist_id, old_status, new_status)
    VALUES (OLD.id, OLD.watch_status, NEW.watch_status);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_watchlist_status_change
AFTER UPDATE OF watch_status ON watchlist
FOR EACH ROW
WHEN (OLD.watch_status IS DISTINCT FROM NEW.watch_status)
EXECUTE FUNCTION log_watchlist_status_change();


CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_watchlist_updated_at
BEFORE UPDATE ON watchlist
FOR EACH ROW
WHEN (OLD IS DISTINCT FROM NEW)
EXECUTE FUNCTION update_timestamp();


CREATE OR REPLACE FUNCTION validate_rating()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.rating IS NOT NULL AND NEW.watch_status != 'watched' THEN
        RAISE EXCEPTION 'Rating allowed only when status is watched';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_rating
BEFORE INSERT OR UPDATE ON watchlist
FOR EACH ROW
EXECUTE FUNCTION validate_rating();