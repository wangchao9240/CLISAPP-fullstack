import cdsapi
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cams_connection():
    key = os.getenv("COPERNICUS_CDS_API_KEY")
    print(f"Testing with key: {key}")
    
    urls_to_test = [
        "https://ads.atmosphere.copernicus.eu/api",
        "https://ads.atmosphere.copernicus.eu",
    ]
    
    for url in urls_to_test:
        print(f"\n--------------------------------------------------")
        print(f"Testing URL: {url}")
        os.environ["CDSAPI_URL"] = url
        try:
            client = cdsapi.Client()
            print("Client initialized.")
            client.retrieve(
                'cams-global-atmospheric-composition-forecasts',
                {
                    'date': '2025-11-20',
                    'type': 'forecast',
                    'format': 'netcdf',
                    'variable': 'particulate_matter_2.5um',
                    'time': '00:00',
                    'leadtime_hour': '0',
                    'area': [0, 0, 1, 1],
                },
                'test_cams.nc'
            )
            print("✅ Retrieve successful!")
            break
        except Exception as e:
            print(f"❌ Retrieve failed: {e}")

if __name__ == "__main__":
    test_cams_connection()
