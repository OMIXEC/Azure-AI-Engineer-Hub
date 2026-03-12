from dotenv import load_dotenv
from datetime import datetime
import os
import azure.cognitiveservices.speech as speech_sdk

def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    try:
        global speech_config

        # Get config settings
        load_dotenv()
        speech_key = os.getenv('AI_SERVICE_KEY') or "7wuX8LKfmS10qDChHeTdE7CA0oV0LjRAPNFPRsZs67b0J4iK09BiJQQJ99CCACYeBjFXJ3w3AAAYACOGiNem"
        speech_region = "eastus"

        # Configure speech service
        speech_config = speech_sdk.SpeechConfig(subscription=speech_key, region=speech_region)
        print("Ready to use speech service in:", speech_region)

        print("\n--- Interactive Speaking Clock ---")
        print("Ask 'What time is it?' or say 'quit' to exit.")

        while True:
            # Get spoken input
            command = TranscribeCommand()
            if command.lower() == 'quit.':
                print("Exiting...")
                break
            
            if 'what time' in command.lower():
                TellTime()
            elif command:
                print(f"You said: {command}")
                print("Try asking 'What time is it?'")

    except Exception as ex:
        print(f"Error in main: {ex}")

def TranscribeCommand():
    command = ''

    # Configure speech recognition
    audio_config = speech_sdk.AudioConfig(use_default_microphone=True)
    speech_recognizer = speech_sdk.SpeechRecognizer(speech_config, audio_config)
    
    print("\nListening...")

    # Process speech input
    result = speech_recognizer.recognize_once_async().get()
    
    if result.reason == speech_sdk.ResultReason.RecognizedSpeech:
        command = result.text
        print(f"Recognized: {command}")
    elif result.reason == speech_sdk.ResultReason.NoMatch:
        print("No speech could be recognized.")
    elif result.reason == speech_sdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"Speech recognition canceled: {cancellation.reason}")
        if cancellation.reason == speech_sdk.CancellationReason.Error:
            print(f"Error details: {cancellation.error_details}")

    # Return the command
    return command


def TellTime():
    now = datetime.now()
    response_text = 'The time is {}:{:02d}'.format(now.hour,now.minute)

    # Configure speech synthesis
    audio_config = speech_sdk.audio.AudioOutputConfig(use_default_speaker=True)
    speech_synthesizer = speech_sdk.SpeechSynthesizer(speech_config, audio_config)

    # Synthesize spoken output
    print(response_text)
    speak = speech_synthesizer.speak_text_async(response_text).get()
    if speak.reason != speech_sdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesis failed: {speak.reason}")


if __name__ == "__main__":
    main()