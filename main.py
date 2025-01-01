from dotenv import load_dotenv
import os
import requests
import json
import pyttsx3
import speech_recognition as sr
import re
import threading 
import time 



API_KEY = os.getenv("API_KEY")
PROJECT_TOKEN = os.getenv("PROJECT_TOKEN")
RUN_TOKEN = os.getenv("RUN_TOKEN")

#class that parses through data
class Data:
	def __init__(self, api_key, project_token):
		self.api_key = api_key
		self.project_token = project_token
		self.params = {
			"api_key": self.api_key #authentication
		}
		self.data = self.get_data()
    #calls request and sets the data attribute for the object
	def get_data(self):
		response = requests.get(f'https://www.parsehub.com/api/v2/projects/{self.project_token}/last_ready_run/data', params=self.params)
		data = json.loads(response.text)
		return data
    #need to set up methods that give us specific data (total cases, total deaths, information about certain countries)
	def get_total_cases(self): #only pertains to data associated with the total list 
		data = self.data['total']

		for content in data:
			if content['name'] == "Coronavirus Cases:":
				return content['value'] #loop through list and return content associated with 'Coronovirus Cases' as the name

	def get_total_deaths(self): #only pertains to data associated with the total list 
		data = self.data['total']

		for content in data:
			if content['name'] == "Deaths:":
				return content['value']

		return "0" #for the case where there is nothing to be returned

	def get_country_data(self, country):
		data = self.data["country"]

		for content in data:
			if content['name'].lower() == country.lower():
				return content #returns content associated with that country (not a specific type of data - unless otherwise specified)

		return "0"

	def get_list_of_countries(self):
		countries = []
		for country in self.data['country']:
			countries.append(country['name'].lower())

		return countries

	def update_data(self): #this method is to ensure that the data is automatically updated 
		response = requests.post(f'https://www.parsehub.com/api/v2/projects/{self.project_token}/run', params=self.params) #post request to a URL that makes a new run
        #using a new thread to check the endpoint - last_ready_run (to see whether or not there is new data)
		def poll():
			time.sleep(0.1)
			old_data = self.data
			while True:
				new_data = self.get_data()
				if new_data != old_data: #check if this data (new_data) is not the same as old data
					self.data = new_data
					print("Data updated")
					break
				time.sleep(5)


		t = threading.Thread(target=poll) #useful as this only affects the voice assistant without having to wait longer to get the updated data (without threading)
		t.start() #start thread


def speak(text): #function that allows the inputted text to actually be said 
	engine = pyttsx3.init()
	engine.say(text)
	engine.runAndWait()


def get_audio():
	r = sr.Recognizer() #speech recognizer
	with sr.Microphone() as source:
		audio = r.listen(source)
		said = "" #whatever is said is stored in the "said" variable

		try:
			said = r.recognize_google(audio) #recognizer provides us with that was said in text format
		except Exception as e:
			print("Exception:", str(e))

	return said.lower()


def main(): #for speech and recognition of speech (to happen back and forth)
	print("Started Program")
	data = Data(API_KEY, PROJECT_TOKEN)
	END_PHRASE = "stop" #this is how loop will end (if program hears stop, the program will be exited)
	country_list = data.get_list_of_countries()
    #dictionary that has patterns that map to a function (useful for implementation of search patterns) - using RegEx search patterns for this
    #function is the value that you want to "speak out" or return
	TOTAL_PATTERNS = {
					re.compile("[\w\s]+ total [\w\s]+ cases"):data.get_total_cases, # (any # of words) + total + (any # of words) + cases
					re.compile("[\w\s]+ total cases"): data.get_total_cases,
                    re.compile("[\w\s]+ total [\w\s]+ deaths"): data.get_total_deaths,
                    re.compile("[\w\s]+ total deaths"): data.get_total_deaths
					}

	COUNTRY_PATTERNS = {
					re.compile("[\w\s]+ cases [\w\s]+"): lambda country: data.get_country_data(country)['total_cases'],
                    re.compile("[\w\s]+ deaths [\w\s]+"): lambda country: data.get_country_data(country)['total_deaths'],
					}

	UPDATE_COMMAND = "update" #verbal command for updated data

	while True:
		print("Listening...")
		text = get_audio()
		print(text)
		result = None

		for pattern, func in COUNTRY_PATTERNS.items():
			if pattern.match(text):
				words = set(text.split(" ")) #easier to identify whether or not a country is within a set by using .split and set
				for country in country_list:
					if country in words:
						result = func(country)
						break
        #want to loop through TOTAL_PATTERNS and check whether or not the text matches that
		for pattern, func in TOTAL_PATTERNS.items(): #gets pattern and the associated function for each of the patterns 
			if pattern.match(text):
				result = func() #call the function associated to the pattern (regardless of what pattern is matched)
				break

		if text == UPDATE_COMMAND:
			result = "Data is being updated. This may take a moment!"
			data.update_data()

		if result:
			speak(result)

		if text.find(END_PHRASE) != -1:  #if stop is found anywhere in the text, the loop will break 
			print("Exit")
			break

main()