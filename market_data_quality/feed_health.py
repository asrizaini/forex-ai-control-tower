def feed_is_fresh(age_seconds: int, max_age_seconds: int = 10) -> bool:
    return age_seconds <= max_age_seconds
