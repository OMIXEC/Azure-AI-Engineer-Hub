from dotenv import load_dotenv
import os
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

def main():
    try:
        # Get Configuration Settings
        load_dotenv()
        translatorRegion = "eastus"
        translatorKey = "7bsp2nhLQ5rpTqsjdFP7sX3dxl4SR8a4N0Njrc9l5QPsdylRoWdGJQQJ99CCACYeBjFXJ3w3AAAbACOGXIvW"
        translatorEndpoint = "https://api.cognitive.microsofttranslator.com/"

        # Create client using endpoint and key
        credential = AzureKeyCredential(translatorKey)
        client = TextTranslationClient(credential=credential, endpoint=translatorEndpoint, region=translatorRegion)

        print("\n--- Azure Interactive Translator ---")
        print("Type 'quit' to exit.")

        while True:
            # Choose target language
            target_language = input("\nEnter target language code (e.g., 'fr', 'es', 'de', 'ja') or press Enter for 'fr': ").strip()
            if target_language.lower() == 'quit':
                break
            if not target_language:
                target_language = 'fr'

            # Get text to translate
            text_to_translate = input(f"Enter the text you want to translate to '{target_language}': ").strip()
            if text_to_translate.lower() == 'quit':
                break
            if not text_to_translate:
                print("Please enter some text.")
                continue

            # Translate text
            print(f"\nTranslating: '{text_to_translate}'...")
            response = client.translate(body=[text_to_translate], to_language=[target_language])
            
            translation = response[0]
            if translation:
                for t in translation.translations:
                    print(f"Result ({t.to}): {t.text}")
            else:
                print("No translation results found.")

    except Exception as ex:
        print(f"\nError: {ex}")

if __name__ == "__main__":
    main()