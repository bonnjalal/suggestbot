import logging
import requests
from time import sleep
from typing import Iterator, List, Dict
import pywikibot
from pywikibot.tools import batched
from pywikibot.page import PageRevIdGenerator
import json

class LiftWingPredictionError(Exception):
    """Custom exception for Lift Wing prediction errors."""
    pass

def get_batch_predictions(
    site: pywikibot.Site,
    pages: List[pywikibot.Page],
    step: int = 50,
    max_retries: int = 3,
    retry_delay: float = 0.5
) -> Iterator[pywikibot.Page]:
    """
    Get article quality predictions using Wikimedia's Lift Wing ML Platform.
    """
    # Process one page at a time initially to debug
    batch_size = 1
    wiki_db = f'{site.lang}wiki'
    
    endpoint = f'https://api.wikimedia.org/service/lw/inference/v1/models/{wiki_db}-articlequality'
    
    for page in pages:
        try:
            rev_id = page.latest_revision_id
            if not rev_id:
                logging.warning(f"No revision ID found for page {page.title()}")
                continue

            # Simplified payload based on Lift Wing documentation
            payload = {
                "rev_id": rev_id,
                "text": page.text,  # Include page text
                "page_title": page.title()
            }

            logging.debug(f'Request payload for {page.title()}: {json.dumps(payload, indent=2)}')
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        endpoint,
                        headers={
                            'User-Agent': config.http_user_agent,
                            'From': config.http_from,
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        },
                        json=payload,
                        timeout=30
                    )
                    
                    logging.debug(f'Response status: {response.status_code}')
                    logging.debug(f'Response headers: {response.headers}')
                    logging.debug(f'Response content: {response.text}')
                    
                    if response.status_code == 500:
                        logging.error(f"Server error (500) for page {page.title()}. Response: {response.text}")
                        if attempt == max_retries - 1:
                            continue  # Skip this page and move to next
                        sleep(retry_delay * (attempt + 1))
                        continue
                        
                    response.raise_for_status()
                    prediction_data = response.json()
                    
                    # Extract prediction
                    if 'prediction' in prediction_data:
                        prediction = prediction_data['prediction'].lower()
                        page.set_prediction(prediction)
                        yield page
                    
                    break  # Success - exit retry loop
                    
                except requests.exceptions.RequestException as e:
                    logging.error(f"Request failed for page {page.title()} on attempt {attempt + 1}: {str(e)}")
                    if attempt == max_retries - 1:
                        continue  # Skip this page and move to next
                    sleep(retry_delay * (attempt + 1))
                    
                except (ValueError, KeyError) as e:
                    logging.error(f"Error parsing response for page {page.title()} on attempt {attempt + 1}: {str(e)}")
                    if attempt == max_retries - 1:
                        continue  # Skip this page and move to next
                    sleep(retry_delay * (attempt + 1))
                    
        except Exception as e:
            logging.error(f"Error processing page {page.title()}: {str(e)}")
            continue

# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG level for detailed logs
    
    try:
        site = pywikibot.Site('en', 'wikipedia')
        # Test with a known valid page
        test_page = pywikibot.Page(site, 'Main Page')
        
        for page in get_batch_predictions(site, [test_page]):
            print(f"Page: {page.title()}, Prediction: {page.prediction}")
            
    except Exception as e:
        logging.error(f"Error: {str(e)}")
