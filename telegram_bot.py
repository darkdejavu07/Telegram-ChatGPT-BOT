import os
import telebot
import requests
import speech_recognition as sr
import subprocess
import datetime
from datetime import timedelta
import whisper
from docx import Document
import os
import openai
from openai import OpenAI

logfile = str(datetime.date.today()) + '.log'
token = 'TELEGRAM_TOKEN'
bot = telebot.TeleBot(token)
openai.api_key = 'OPENAI_TOKEN'
max_token_count = 4096
client = OpenAI(api_key=openai.api_key)

def audio_to_text(dest_name: str):

    r = sr.Recognizer()
    message = sr.AudioFile(dest_name)
    with message as source:
        audio = r.record(source)
    result = r.recognize_google(audio, language="ru_RU") # здесь можно изменять язык распознавания
    return result

@bot.message_handler(content_types = ['document'])
def get_document_messages(message):
	try:
		print(message.content_type)
		chat_id = message.chat.id
		file_info = bot.get_file(message.document.file_id)
		downloaded_file = bot.download_file(file_info.file_path)
		src = 'input.wav';
		with open(src, 'wb') as new_file:
			new_file.write(downloaded_file)
		bot.reply_to(message, "Saved...Start decoding.")
		audio = whisper.load_audio('input.wav')
		audio = whisper.pad_or_trim(audio)
		model_name = 'small'
		model = whisper.load_model(model_name)
		mel = whisper.log_mel_spectrogram(audio).to(model.device)
		result = model.transcribe('input.wav',)
		segments = result['segments']
		text_massive = []
		for segment in segments:
			text = segment['text']
			segment = f"{text if text[0] == ' ' else text}"
			print(segment)
			text_massive.append(segment)
		text = text_massive
		doc = Document()
		for key in text:
			doc.add_paragraph(key)
		doc.save(message.document.file_name + '.docx')
		file = open(message.document.file_name + '.docx', "rb")
		bot.send_document(message.from_user.id,file)
		os.remove('input.wav')
		os.remove(message.document.file_name + '.docx')
		with open(logfile, 'a', encoding='utf-8') as f:
			f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + '	 ' + str(message.from_user.id) + ':' +  str(message.from_user.first_name) + str('. Transcribate audio: ') + str(message.document.file_name) + '\n')
	except sr.UnknownValueError as e:
		bot.send_message(message.from_user.id,  "Прошу прощения, но я не разобрал сообщение, или оно пустое...")
		with open(logfile, 'a', encoding='utf-8') as f:
			f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + ':' + str(message.from_user.id) + ':' + str(message.from_user.first_name) + '_' + str(message.from_user.last_name) + ':' + str(message.from_user.username) +':'+ str(message.from_user.language_code) + ':Message is empty.\n')
	finally:
		print ('Finished...')

@bot.message_handler(content_types=['voice'])
def get_audio_messages(message):
	try:
		print (message.content_type)
		print("Started recognition...")
		file_info = bot.get_file(message.voice.file_id)
		path = file_info.file_path
		fname = os.path.basename(path)
		filename = str(message.from_user.id) + '_' + str(datetime.datetime.today().strftime("%H%M%S")) + '_'
		fname = filename + fname
		print ('fname: ' + fname)
		print ('filename: ' + filename)
		doc = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path))
		with open(fname+'.oga', 'wb') as f:
			f.write(doc.content)
		process = subprocess.run(['ffmpeg', '-i', fname+'.oga', fname+'.wav'])
		result = audio_to_text(fname+'.wav')
	except sr.UnknownValueError as e:
		bot.send_message(message.from_user.id,  "Прошу прощения, но я не разобрал сообщение, или оно пустое...")
		with open(logfile, 'a', encoding='utf-8') as f:
			f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + ':' + str(message.from_user.id) + ':' + str(message.from_user.first_name) + '_' + str(message.from_user.last_name) + ':' + str(message.from_user.username) +':'+ str(message.from_user.language_code) + ':Message is empty.\n')
	finally:
		os.remove(fname+'.wav')
		messages = [
			{
				"role": "system",
				"content": result
			}
]
		response = client.chat.completions.create(
			model="gpt-3.5-turbo-16k-0613",
			messages=messages,
			max_tokens=max_token_count,
		)
		answerbot = (response.choices[0].message.content)
		print ('Question:	' + str(result))
		print ('Answer:		' + str(answerbot))
		with open(logfile, 'a', encoding='utf-8') as f:
			f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + '	 ' + str(message.from_user.id) + ':' +  str(message.from_user.first_name) + '. Question: ' + str(result) + '. Answer: ' + str(answerbot) + '\n')
		respaudio = client.audio.speech.create(
			model="tts-1", # the model to use, there is tts-1 and tts-1-hd
			voice="shimmer", # the voice to use, there is alloy, echo, fable, onyx, nova, and shimmer
			input=answerbot, # the text to generate speech from
			speed=0.9, # the speed of the generated speech, ranging from 0.25 to 4.0
		)
		respaudio.stream_to_file('audio.oga')
		bot.send_audio(message.from_user.id, audio=open('audio.oga', 'rb'))
		os.remove('audio.oga')
@bot.message_handler(commands=['image'])
def get_photo_messages(message):
	bot.reply_to(message, "Generate image. Please wait...")
	print ('Generate image ' + str(message.text[7:]))
	response = client.images.generate(
		prompt=message.text,
		n=1,
		size="1024x1024",
	)
	bot.send_photo(message.from_user.id, response.data[0].url)
	with open(logfile, 'a', encoding='utf-8') as f:
		f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + '	 ' + str(message.from_user.id) + ':' +  str(message.from_user.first_name) + str('. Generate image: ') + str(message.text[7:]) + '\n')
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
	messages = [
    {
        "role": "system",
        "content": message.text
    }
]
	chat_completion = client.chat.completions.create(
		model="gpt-3.5-turbo-1106",
		messages=messages,
	)
	response = chat_completion.choices[0].message.content
	bot.send_message(message.from_user.id, response)
	print (message.text)
	print (response)
	with open(logfile, 'a', encoding='utf-8') as f:
			f.write(str(datetime.datetime.today().strftime("%H:%M:%S")) + '	 ' + str(message.from_user.id) + ':' +  str(message.from_user.first_name) + '. Question: ' + str(message.text) + '. Answer: ' + str(response) + '\n')
bot.polling(none_stop=True, interval=0)
