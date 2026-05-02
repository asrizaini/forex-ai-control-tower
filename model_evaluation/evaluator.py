def evaluate_model_result(result: dict) -> dict:
    return {"score": result.get("score", 0), "accepted": result.get("score", 0) >= 70}
