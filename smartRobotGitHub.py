
'''
Author: Joshua Duvnjak
Description:

Required Hardware: Picar X AI, Raspberry Pi 4

References: Code from the Picar X AI/vilib documentation by Sunfounder and SpeechRecognition Python Module
https://docs.sunfounder.com/projects/picar-x-v20/en/latest/index.html
https://docs.sunfounder.com/projects/vilib-rpi/en/latest/index.html
https://docs.sunfounder.com/projects/picar-x-v20/en/latest/python/python_avoid.html
https://docs.sunfounder.com/projects/vilib-rpi/en/latest/py_display.html
https://github.com/Uberi/speech_recognition/blob/master/examples/microphone_recognition.py
'''

#Import modules
from picarx import Picarx
from vilib import Vilib
from picarx.tts import Espeak
import time
import speech_recognition as sr
from google import genai
import os

#Capture and Transcribe user speech; code from SpeechRcognition examples (see ref above)
def captureUserSpeech(line):

    #Capture user speech
    recogniserObject = sr.Recognizer()
    with sr.Microphone() as source:
        
        #Query the user
        tts.say(line)

        #Listen for the user input
        user_voice = recogniserObject.listen(source)


    #Transcribe and return user speech
    try:
        return recogniserObject.recognize_sphinx(user_voice)
    except sr.UnknownValueError:
        print('Audio Error')
        return



#Use Gemini AI as a decision selector 
def genAIActionSelector(userInput):

    #Call the Google Gemini API to work out the next action to take
    genAIResponse = AIGemini.models.generate_content(model='gemini-2.5-flash',
                                        contents='You are a helper robot, decide whether to stop or to answer a question for the user input of the words: '+userInput,
                                        config={
                                            'response_mime_type':'text/x.enum',
                                            'response_schema': {
                                                'type':'STRING',
                                                'enum': ['Answer Question','Stop','Greeting'],
                                            }
                                        }
                                        )


    #Return the question, or the action if not a qustion
    if genAIResponse.text == 'Answer Question':
        genAIResponse = AIGemini.models.generate_content(model='gemini-2.5-flash',
                                                        contents=userInput)
        return genAIResponse.text.replace('*',' ')
    elif genAIResponse.text == 'Stop' or genAIResponse.text == 'Greeting':
        return genAIResponse.text
    else:
        tts.say('Gen AI error')
    

#When the ultrasonic sensor has detected a close object enable the camera
def cameraSearch(cameraPanAngle,cameraTiltAngle,state):

    try:
        #Start the image classifier
        Vilib.camera_start(vflip=False,hflip=False)
        Vilib.display(local=False,web=False)
    

        #Start the image classifier to look for users
        Vilib.face_detect_switch(True)

    except:
        pass

    #Look in six directions for a user (or indication of a user)
    for tiltAngle in [0,30]:
        #Set Camera title
        px.set_cam_tilt_angle(tiltAngle)
        
        #Set a time to be compared against
        searchTime = time.time()

        for panAngle in [-30,0,30]:
            #Set camera pan
            px.set_cam_pan_angle(panAngle)

            #Wait to allow for image classification
            while searchTime +7 > time.time():
                if Vilib.detect_obj_parameter['human_n'] > 0:
                    state = 'visual'
                    Vilib.face_detect_switch(False)
                    Vilib.camera_close()
                    return state, time.time()
    
            
    #Stop the classifier
    Vilib.face_detect_switch(False)

    return state, time.time()

#Search for users by driving and the camera
def search(state):

    #State callout 
    tts.say('Searching for User')

    #Set a variable to avoid contant searching
    searchTime = time.time()

    while True:
        #Reset camera position
        cameraPanAngle = 0
        cameraTiltAngle = 0

        #Set the speed
        picarSpeed = 5

        #Read the ultrasonic sensor
        ultrasonicDistance = round(px.ultrasonic.read(),1)

        print(ultrasonicDistance)
        
        #If the Picar is far away from an object then move forwards
        if ultrasonicDistance > 40:
            px.set_dir_servo_angle(0)
            px.forward(picarSpeed)
        #If not too close to an object turn around it
        elif ultrasonicDistance < 20:
            px.set_dir_servo_angle(30)
            px.forward(picarSpeed)
        #If within a short distance activate the camera search
        else:
            #If five seconds have passed since the last search
            if searchTime +5 < time.time():
                state, searchTime  = cameraSearch(cameraPanAngle,cameraTiltAngle,state)

            #Break out of this state if a user was found
            if state == 'visual':
                return state
            
            #Reverse backwards if no user was found
            px.set_dir_servo_angle(0)
            px.backward(picarSpeed)


#When a user is found confirm they wish to engage with the robot
def speakToUser(state):

    #Acknowledge user and collect response
    userVoice = captureUserSpeech('Hello')

    #Work out what type of response the user gave
    AIResponse = genAIActionSelector(userVoice)
    
    #If a greeting change state
    if AIResponse == 'Greeting':
        state = 'visualAndSound'
    else:
        #try to repair conversation and collect response
        userVoice = captureUserSpeech('Hello, please respond with a greeting')

        #Work out what type of response the user gave
        AIResponse = genAIActionSelector(userVoice)

        #If a greeting change state to assistant
        if AIResponse == 'Greeting':
            state = 'visualAndSound'
        else:
            #There isn't a user go back to search state
            state = 'search'
    
    return state

def smartAgent(state):
    
    while True:
        #Acknowledge user and collect response
        userVoice = captureUserSpeech('Do you have a question')

        #Work out what type of response the user gave
        AIResponse = genAIActionSelector(userVoice)
    
        #If a Stop change state to basic
        if AIResponse == 'Stop':
            state = 'search'
        #If greeting respond
        elif AIResponse == 'Greeting':
            tts.say('Hello')
        else:
            #Answer the question
            tts.say(AIResponse)
        
        return state

if __name__ == '__main__':

    #Set the API key for the Google Gemini model
    AIGemini = genai.Client(api_key='')

    #Start the picar
    px = Picarx()

    #Start the text to speech
    tts = Espeak()

    #Start the state machine
    state = 'search'

    
    #Set states in the state machine
    while True:
        #Searching for users
        if state == 'search':
            tts.say('State Search')
            state = search(state)
        #User has been found with the camera
        elif state == 'visual':
            tts.say('State Visual')
            state = speakToUser(state)
        #User has been found visually and by sound
        elif state == 'visualAndSound':
            tts.say('visual and sound')
            state = smartAgent(state)
        #State error
        else:
            tts.say('State error')
