from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mhandler import MHandler
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

import configparser

# Bot's Matrix credentials
M_USERNAME = ""
M_PASSWORD = ""
M_SERVER = ""

# List of ongoing motions. One per room
ONGOING_MOTIONS = []

# List of incomplete motion objects that are being created
ONGOING_MOTIONCREATIONS = []

# List of ended motions. Only stores one per room
ENDED_MOTIONS = []

class AllMessageHandler(MHandler):
    def __init__(self, handle_callback):
        MHandler.__init__(self, self.check_update, handle_callback)

    def check_update(self, room, event):
        if event['type'] == "m.room.message":
            return True
        return False

class Vote(object):
    def __init__(self, user_id, choice_idx):
        self.user_id = user_id
        self.choice_idx = choice_idx

class Motion(object):
    def __init__(self, room_id, creator, question, choices):
        self.room_id = room_id
        self.creator = creator
        self.question = question
        self.choices = choices
        self.votes = []


def motion_callback(room, event): #SG2
    # Make sure we don't have an ongoing motion for this room
    for motion in ONGOING_MOTIONS:
        if motion.room_id == room.room_id:
            room.send_text("There's already an ongoing motion in this room! Please end it before starting a new one.")
            return

    # Make sure we don't have an ongoing motion creation for this room
    for motion in ONGOING_MOTIONCREATIONS:
        if motion.room_id == room_id:
            room.send_text("There's already an ongoing motion in this room! Please end it before starting a new one.")
            return


    # Create an incomplete Motion object and add it to ONGOING_MOTIONCREATIONS
    new_motion = Motion(room.room_id, event['sender'], None, None)
    ONGOING_MOTIONCREATIONS.append(new_motion)

    # Prompt the user for a question
    room.send_text("Creating a new motion. Please send the question.") #SG2

    # When they respond, it will be handled by the ongoing handler

# Handles ongoing motion creations
def ongoing_motion_callback(room, event):
    # Make sure this room has an ongoing motion creation and it was created by the message sender
    if event['content']['body'][0] == '!':
        return

    motion =  None
    for p in ONGOING_MOTIONCREATIONS:
        if p.room_id == room.room_id and p.creator == event['sender']:
            motion = p
            break
    if motion is None:
        return

    # See which part to handle
    if motion.question is None:
        motion.question = event['content']['body']
        motion.choices = ['aye','nay','abstain'] #SG
        #SG room.send_text("Okay, now send me the choices. Type !startmotion to start the motion.")
        room.send_text("Ready. Type !startmotion to start the motion.") #SG
        
    else:
        # Handle message as a choice
        if motion.choices is None:
            motion.choices = []
            
        motion.choices.append(event['content']['body'])
        room.send_text("Response added. Send another choice or type !startmotion to start the motion")


# Starts a motion (moves from an ongoing motion creation to an ongoing motion)
def startmotion_callback(room, event):
    # Make sure there's an ongoing motion creation and it was created by the message sender
    motion =  None
    for p in ONGOING_MOTIONCREATIONS:
        if p.room_id == room.room_id and p.creator == event['sender']:
            motion = p
            break
    if motion is None:
        room.send_text("There are no motions you can start!")
        return

    # Confirm that the motion is ready and move it from ONGOING_MOTIONCREATIONS to ONGOING_MOTIONS
    if motion.question is None:
        room.send_text("You need to send a question first!")
        return

    if motion.choices is None or len(motion.choices) < 2:
        room.send_text("You need to send at least two choices first!")
        return

    # Remove the motion from ONGOING_MOTIONCREATIONS and add to ONGOING_MOTIONS
    ONGOING_MOTIONCREATIONS.remove(motion)
    ONGOING_MOTIONS.append(motion)

    room.send_text("Motion started! Repeat the question with !info")
    info_callback(room, event)

# Display ongoing motion/choices and results
def info_callback(room, event):
    # Make sure there's an ongoing motion in the room
    motion = None
    for p in ONGOING_MOTIONS:
        if p.room_id == room.room_id:
            motion = p
            break
    if motion is None:
        room.send_text("There are no currently ongoing motions! Start a new one with !motion") #SG2
        return

    response_str = ""

    # Add the question
    response_str += motion.question + "\n"
    response_str += "-" * len(motion.question) + "\n"

    # Add each choice along with its votes
    for i in range(0, len(motion.choices), 1):
        # Add this choice along with the number of votes it recieved
        num_votes = len([x for x in motion.votes if x.choice_idx == i])
        response_str += "%d. %s: %d votes\n" % (i+1, motion.choices[i], num_votes)

    # Add the ending message
    response_str += "To vote, do !vote <number>\n"
    response_str += "To end the motion, run !endmotion"

    room.send_text(response_str)

# End a motion and move it from ONGOING_MOTIONS to ENDED_MOTIONS
def endmotion_callback(room, event):
    # Make sure there's an ongoing motion in the room
    motion = None
    for p in ONGOING_MOTIONS:
        if p.room_id == room.room_id:
            motion = p
            break
    if motion is None:
        room.send_text("There are no currently ongoing motions! Start a new one with !motion") #SG2
        return

    # Make sure the sender is the creator of the motion
    if motion.creator != event['sender']:
        room.send_text("You can only end motions that you have created!")
        return

    # Remove the motion from ONGOING_MOTIONS and add to ENDED_MOTIONS
    ONGOING_MOTIONS.remove(motion)

    # Remove all ended motions that belong to this room
    global ENDED_MOTIONS
    ENDED_MOTIONS = [x for x in ENDED_MOTIONS if x.room_id != room.room_id]
    ENDED_MOTIONS.append(motion)

    room.send_text("Motion ended! See results with !results")
    results_callback(room, event)

# Display the results for an ended motion
def results_callback(room, event):
    # Make sure this room has an ended motion
    motion = None
    for p in ENDED_MOTIONS:
        if p.room_id == room.room_id:
            motion = p
            break
    if motion is None:
        room.send_text("There are no previous motions to view!")
        return

    response_str = ""

    # Add the question
    response_str += motion.question + "\n"
    response_str += "-" * len(motion.question) + "\n"

    # Add each choice along with its votes
    for i in range(0, len(motion.choices), 1):
        # Add this choice along with the number of votes it recieved
        num_votes = len([x for x in motion.votes if x.choice_idx == i])
        response_str += "%d. %s: %d votes\n" % (i+1, motion.choices[i], num_votes)

    # Add the ending message
    response_str += "To start a new motion, run !motion\n" #SG2
    room.send_text(response_str)

# Vote for an ongoing motion
def vote_callback(room, event):
    # Make sure that this room has an ongoing motion
    motion = None
    for p in ONGOING_MOTIONS:
        if p.room_id == room.room_id:
            motion = p
            break
    if motion is None:
        room.send_text("There are no currently ongoing motions! Start a new one with !motion") #SG2
        return

    # Verify arguments
    args = event['content']['body'].split(' ')
    if len(args) != 2:
        room.send_text("Usage: !vote <number>")
        return


    # If this user has already voted, remove their previous vote
    motion.votes = [x for x in motion.votes if x.user_id != event['sender']]

    # Get the index of their choice
    choice_idx = 0
    try:
        choice_idx = int(args[1]) - 1
    except:
        room.send_text("Usage: !vote <number>")
        return

    # Verify that the given number corresponds to a choice
    if choice_idx < 0 or choice_idx >= len(motion.choices):
        room.send_text("Please pick a valid choice! Run !info to repeat the motion")
        return

    # Add this vote
    motion.votes.append(Vote(event['sender'], choice_idx))

    # Get this user's short name (not including server)
    short_name = event['sender'][:event['sender'].index(':')]

    # Get the choice they voted for
    choice = motion.choices[choice_idx]

    room.send_text("%s has voted for '%s'!\n!info - Show current results" % (short_name, choice))


# Print help
def motionhelp_callback(room, event):
    help_str =  "!motion    - Create a new motion\n" #SG2
    help_str += "!startmotion - Start a motion\n"
    help_str += "!info      - View an ongoing motion\n"
    help_str += "!vote      - Vote in an ongoing motion\n"
    help_str += "!endmotion   - End an ongoing motion\n"
    help_str += "!results   - View the results of the last ended motion"
    room.send_text(help_str)


def main():
    # Load configuration
    config = configparser.ConfigParser()
    config.read("config.ini")
    username = config.get("Matrix", "Username")
    password = config.get("Matrix", "Password")
    server = config.get("Matrix", "Homeserver")

    # Start bot
    bot = MatrixBotAPI(username, password, server)

    m_motion_handler = MCommandHandler('motion', motion_callback) #SG2
    bot.add_handler(m_motion_handler) #SG2

    m_ongoing_motion_handler = AllMessageHandler(ongoing_motion_callback)
    bot.add_handler(m_ongoing_motion_handler)

    m_startmotion_handler = MCommandHandler('startmotion', startmotion_callback)
    bot.add_handler(m_startmotion_handler)

    m_info_handler = MCommandHandler('info', info_callback)
    bot.add_handler(m_info_handler)

    m_endmotion_handler = MCommandHandler('endmotion', endmotion_callback)
    bot.add_handler(m_endmotion_handler)

    m_results_handler = MCommandHandler('results', results_callback)
    bot.add_handler(m_results_handler)

    m_vote_handler = MCommandHandler('vote', vote_callback)
    bot.add_handler(m_vote_handler)

    m_motionhelp_handler = MCommandHandler('motionhelp', motionhelp_callback)
    bot.add_handler(m_motionhelp_handler)


    bot.start_motioning()
    print("Motionbot started!")

    while True:
        input()




if __name__ == "__main__":
    main()
