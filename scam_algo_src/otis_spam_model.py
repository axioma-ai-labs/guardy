from transformers import pipeline
import time
import logging

# set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# load the spam classification model
try:
    classification_pipeline = pipeline("text-classification", model="Titeiiko/OTIS-Official-Spam-Model")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    classification_pipeline = None

def is_greeting(input_text: str):
    """
    check if the input text contains common greeting phrases.

    parameters:
    - input_text (str): text to analyze

    returns:
    - bool: true if the input text contains any greeting phrases, false otherwise
    """
    greeting_phrases = ['hello', 'hi', 'good morning', 'good afternoon', 'good evening', 'hey', 'gm', 'gn']
    for greeting in greeting_phrases:
        if greeting in input_text.lower():
            logger.info("Greeting identified!")
            return True
    return False

def analyze_message(input_text: str):
    """
    analyze the input text to determine if it is spam or not.

    parameters:
    - input_text (str): text to analyze

    returns:
    - dict: dictionary containing the probability of spam and the label (spam or not spam)
    """
    if classification_pipeline is None:
        logger.error("Model not loaded properly. Cannot classify the message.")
        return None

    try:
        start_time = time.time()
        result = classification_pipeline(input_text)[0]
        duration = time.time() - start_time

        # check if the message is a greeting
        if is_greeting(input_text):
            # deboost greetings if classified as spam
            if result["label"] == "LABEL_1":
                result["score"] = max(result["score"] - 0.4, 0)  # deboost by 0.4

        tag = "not spam" if result["label"] == "LABEL_0" else "spam"
        logger.info(f"Total time (s): {duration:.3f}")
        return {"probability": result["score"], "label": tag}
    except Exception as e:
        logger.error(f"Error analyzing message: {str(e)}")
        return {"probability": 0, "label": "error"}
