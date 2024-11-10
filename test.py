import logging
import requests
import json
import pywikibot


def get_prediction(page):  # Test for a single page
    try:
        rev_id = page.latest_revision_id
        if not rev_id:
            logging.warning(f"No revision ID found for {page.title()}")
            return None  # Or raise an exception

        page.text  # Force retrieval of page text

        inference_url = 'https://api.wikimedia.org/service/lw/inference/v1/models/enwiki-articlequality:predict'
        headers = {
            'Content-Type': 'application/json', #Keep this
            'User-Agent': 'YOUR_APP_NAME (YOUR_EMAIL_OR_CONTACT_PAGE)' #Use this
        }

        #From the working example
        data = {"rev_id": rev_id, 
                # "text": page.text, 
                "page_title": page.title()}
        #OR From what seems to work in curl
        #data = {"rev_id": rev_id}

        json_data = json.dumps(data, ensure_ascii=False)
        logging.debug(f"JSON Payload: {json_data}")

        response = requests.post(inference_url, headers=headers, data=json_data)
        response.raise_for_status()

        prediction_data = response.json()
        # Correct way to access prediction when only rev_id is sent:
        wiki = page.site.dbName()  # Get wiki db name (e.g., 'enwiki')
        prediction = prediction_data[wiki]['scores'][str(rev_id)]['articlequality']['score']['prediction']



        if prediction:
            return prediction.lower()
        else:
            logging.warning(f"'prediction' key not found in response for {page.title()}")
            return None  # Or raise an exception
        # return prediction_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {page.title()}: {e}")
        if e.response is not None and e.response.text: #Check and log server error
            logging.error(f"Server error message:{e.response.text}")
        return None  # Or raise an exception
    except Exception as e:
        logging.error(f"Error processing {page.title()}: {e}")
        return None # Or raise



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG

    site = pywikibot.Site('en', 'wikipedia')
    page = pywikibot.Page(site, 'Wings of Fire (novel series)')

    prediction = get_prediction(page)
    if prediction:
        print(f"Prediction: {prediction}")
