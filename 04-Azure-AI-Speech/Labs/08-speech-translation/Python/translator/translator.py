from dotenv import load_dotenv
from datetime import datetime
import os
import azure.cognitiveservices.speech as speech_sdk

def main():
    try:
        global speech_config
        global translation_config

        # Get Configuration Settings
        load_dotenv()
        speech_key = os.getenv('AI_SERVICE_KEY') or "7wuX8LKfmS10qDChHeTdE7CA0oV0LjRAPNFPRsZs67b0J4iK09BiJQQJ99CCACYeBjFXJ3w3AAAYACOGiNem"
        speech_region = "eastus"

        # Configure translation
        translation_config = speech_sdk.translation.SpeechTranslationConfig(subscription=speech_key, region=speech_region)
        translation_config.speech_recognition_language = 'en-US'
        translation_config.add_target_language('fr')
        translation_config.add_target_language('es')
        translation_config.add_target_language('hi')
        print('Ready to translate from en-US to fr, es, hi')

        # Configure speech
        speech_config = speech_sdk.SpeechConfig(subscription=speech_key, region=speech_region)

        # Get user input
        targetLanguage = ''
        while targetLanguage != 'quit':
            targetLanguage = input('\nEnter a target language\n fr = French\n es = Spanish\n hi = Hindi\n Enter anything else to stop\n').lower()
            if targetLanguage in ['fr', 'es', 'hi']:
                Translate(targetLanguage)
            else:
                targetLanguage = 'quit'
                

    except Exception as ex:
        print(f"Error in main: {ex}")

def Translate(targetLanguage):
    translation = ''

    # Translate speech
    audio_config = speech_sdk.AudioConfig(use_default_microphone=True)
    translator = speech_sdk.translation.TranslationRecognizer(translation_config, audio_config)
    
    print("Speak now...")
    result = translator.recognize_once_async().get()
    
    if result.reason == speech_sdk.ResultReason.TranslatedSpeech:
        print(f"Recognized: {result.text}")
        translation = result.translations[targetLanguage]
        print(f"Translated to {targetLanguage}: {translation}")
        
        # Synthesize translation
        # (Optional: synthesis logic can be added here)
        
    elif result.reason == speech_sdk.ResultReason.RecognizedSpeech:
        print(f"Speech recognized but not translated: {result.text}")
    elif result.reason == speech_sdk.ResultReason.NoMatch:
        print("No speech could be recognized.")
    elif result.reason == speech_sdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"Speech recognition canceled: {cancellation.reason}")
        if cancellation.reason == speech_sdk.CancellationReason.Error:
            print(f"Error details: {cancellation.error_details}")

if __name__ == "__main__":
    main()
