__author__ = 'ryan'

import tkinter as tk
import os
import time
from PIL import Image, ImageTk
from abc import ABCMeta, abstractmethod
import random
from enum import Enum

class Possession(Enum):
    notinposession = 1
    human = 2
    computer = 3

class TimerBar():
    def __init__(self, canvas, rectangle):
        self.canvas = canvas
        self.rectangle = rectangle

    def update(self, perc_remaining):
        self.canvas.coords(self.rectangle, 1, 1, int(perc_remaining * int(self.canvas.cget("width"))), self.canvas.cget("height"))
        self.canvas.itemconfig(self.rectangle, fill = "#" + ("%02x" % int((1-perc_remaining)*255)) + ("%02x" % int(perc_remaining*255)) + "00" )

    def reset(self):
        self.canvas.coords(self.rectangle, 1, 1, self.canvas.cget("width"), self.canvas.cget("height"))
        self.canvas.itemconfig(self.rectangle, fill = "#00FF00")

class GameTracker:
    def __init__(self, canvas, timer_bar, label_time, label_score, fieldSetup, bluePlayerNames, redPlayerNames, pathToBluePlayerImage, pathToBlueGoalkeeperImage, pathToRedPlayerImage, pathToRedGoalkeeperImage, pathToBallImage):
        self.game_just_finished = False
        self.canvas = canvas
        self.timer_bar = timer_bar
        self.label_time = label_time
        self.label_score = label_score
        self.shot_time = 5
        self.game_time_left = 120

        self.start_positions_blue = [[0, 2], [1, 1], [1, 3], [2, 0], [2, 2], [2, 4]]
        self.start_positions_red = [[3, 0], [3, 2], [3, 4], [4, 1], [4, 3], [5, 2]]
        self.attackMatrix = [[2,2,1,0,0,0],[1,1,2,1,0,0],[0,2,1,1,1,0],[0,1,1,1,1,1],[0,0,1,1,1,2],[0,0,0,1,2,2]]
        self.defenceMatrix = [[2,3,1,0,0,0],[2,2,2,0,0,0],[1,2,2,1,0,0],[0,1,2,2,1,0],[0,0,1,2,2,1],[0,0,1,1,2,2]]

        self.score = [0, 0]
        self.gridWidth = 6
        self.gridHeight = 5
        self.possession = Possession.notinposession
        self.gameRunning = 0
        self.paused = 0
        self.consecutiveBadGuesses = 0

        #create Field
        self.field = Field(self.canvas, self.gridWidth, self.gridHeight, *fieldSetup)

        #Create Players
        self.bluePlayers = self.createPlayers(bluePlayerNames, self.start_positions_blue, pathToBluePlayerImage, pathToBlueGoalkeeperImage, "left")
        self.numBluePlayers = len(self.bluePlayers)
        self.redPlayers = self.createPlayers(redPlayerNames, self.start_positions_red, pathToRedPlayerImage, pathToRedGoalkeeperImage, "right")
        self.numRedPlayers = len(self.redPlayers)

        #create Ball
        (ballStartX, ballStartY) = self.field.getCentreFieldPosition()
        self.ball = Ball(self.canvas, ballStartX, ballStartY, pathToBallImage)

        fieldColour = fieldSetup[6]

        #create small message textbox
        self.message_text = self.canvas.create_text(int(int(self.canvas.cget("width"))/ 2), int(int(self.canvas.cget("height")) * 0.4), text="CLICK PARA COMENZAR", font=("Helvetica", "20"), fill="black")
        a,b,c,d =  self.canvas.bbox(self.message_text)
        self.message_textbox = self.canvas.create_rectangle(a - 10, b - 5, c + 10, d +5, width=0,  fill=fieldColour, outline="black")
        self.canvas.tag_lower(self.message_textbox, self.message_text)

        #create highlight message text
        self.highlight_text = self.canvas.create_text(int(int(self.canvas.cget("width"))/ 2), int(int(self.canvas.cget("height")) * 0.2), text="SPACY SPACER TEXT HERE", font=("Helvetica", "40"), fill="black")
        a,b,c,d =  self.canvas.bbox(self.highlight_text)
        self.highlight_textbox = self.canvas.create_rectangle(a - 10, b - 5, c + 10, d +5, width=0,  fill=fieldColour, outline="black")
        self.canvas.itemconfig(self.highlight_text, state = tk.HIDDEN)
        self.canvas.itemconfig(self.highlight_textbox, state = tk.HIDDEN)


    def startPlay(self):
        self.consecutiveBadGuesses = 0
        self.time_last = time.time()
        self.move_time_left = self.shot_time
        self.wiggle_time_left = 0.1
        self.gameRunning = True
        self.canvas.itemconfig(self.highlight_text, state = tk.HIDDEN)
        self.canvas.itemconfig(self.highlight_textbox, state = tk.HIDDEN)
        self.canvas.itemconfig(self.message_text, state = tk.HIDDEN)
        self.canvas.itemconfig(self.message_textbox, state = tk.HIDDEN)

        if self.score != [0, 0] or self.game_just_finished:     #if someone just scored reset the field
            self.destroyPlayerPuzzles()
            self.ball.setPosition(*self.field.getCentreFieldPosition())
            self.ball.move()
            
            for i in range(1, len(self.bluePlayers)):
                self.bluePlayers[i].setCoords(*self.start_positions_blue[i - 1])
                self.bluePlayers[i].setPosition(*self.field.lookupGridPosition(*self.start_positions_blue[i - 1]))
                self.bluePlayers[i].move()
            
            for i in range(1, len(self.redPlayers)):
                self.redPlayers[i].setCoords(*self.start_positions_red[i - 1])
                self.redPlayers[i].setPosition(*self.field.lookupGridPosition(*self.start_positions_red[i - 1]))
                self.redPlayers[i].move()

        if self.game_just_finished:
            self.possession = Possession.notinposession
            self.game_time_left = 120
            self.score = [0, 0]
            self.game_just_finished = False
            self.label_score.config(text = "0 - 0")

        self.ball.generatePuzzle()


    def update(self):
        if self.gameRunning == True and self.paused == False:
            time_now = time.time()

            self.game_time_left -= time_now - self.time_last
            m, s = divmod(self.game_time_left, 60)

            if self.game_time_left < 0:
                m, s = 0, 0

                if self.score[0] > self.score[1]:
                    message_text = "GAN\xd3 JUGADOR " + str(self.score[0]) + " - " + str(self.score[1])
                    text_colour = "blue"
                elif self.score[1] > self.score[0]:
                    message_text = "GAN\xd3 COMPUTADOR " + str(self.score[1]) + " - " + str(self.score[0])
                    text_colour = "red"
                elif self.score[0] == self.score[1]:
                    message_text = "EMPATE" + str(self.score[0]) + " - " + str(self.score[1])
                    text_colour = "black"

                self.canvas.itemconfig(self.highlight_textbox, state = tk.NORMAL)
                self.canvas.itemconfig(self.highlight_text, text = message_text, fill = text_colour, state = tk.NORMAL)
                self.canvas.tag_raise(self.highlight_textbox)
                self.canvas.tag_raise(self.highlight_text)

                self.canvas.itemconfig(self.message_text, text = "CLICK PARA JUGAR DE NUEVO", state = tk.NORMAL)
                self.canvas.itemconfig(self.message_textbox, state = tk.NORMAL)
                self.canvas.tag_raise(self.message_textbox)
                self.canvas.tag_raise(self.message_text)

                self.gameRunning = False
                self.game_just_finished = True


            self.move_time_left -= time_now - self.time_last
            if self.move_time_left < 0:
                self.possessionLast = self.possession
                self.possession = Possession.computer
                self.initiatePossessionChange()
            else:
                perc_time_left = self.move_time_left / self.shot_time
                self.timer_bar.update(perc_time_left)

            self.wiggle_time_left -= time_now - self.time_last
            if self.wiggle_time_left < 0:
                self.wigglePlayers()
                self.wiggle_time_left = 0.1

            self.label_time.configure(text = "%d : %02d" % (m, s) )

            self.time_last = time_now

    def wigglePlayers(self):
            for x in self.bluePlayers:
                x.wiggle()
            for x in self.redPlayers:
                x.wiggle()

    def handleUserInput(self, inputNumber):
        goodAnswer = False
        goalScored = False
        possessionLast = self.possession
        if self.possession == Possession.notinposession: #No player has possession
            if inputNumber == self.ball.getPuzzleSolution():
                goodAnswer = True

        elif self.possession == Possession.human: #human in possession
            if self.playerInPossession.getCoords()[0] >= self.field.gridWidth - 2:
                if inputNumber == self.redPlayers[0].getPuzzleSolution():   #player kicked goal
                    goodAnswer = True
                    goalScored = True
                    self.kickGoal("right")

            if not goalScored:
                for x in self.bluePlayers:
                    if x != self.playerInPossession and self.bluePlayers.index(x) !=0 : #if not player in possession or goalie
                        if inputNumber == x.getPuzzleSolution():
                            goodAnswer = True
                            receivingPlayer = x
                            break

        elif self.possession == Possession.computer: #computer in possession
            if inputNumber == self.playerInPossession.getPuzzleSolution():
                goodAnswer = True

        if goodAnswer and not goalScored:
            self.possession = Possession.human
        else:
            self.consecutiveBadGuesses += 1

        if self.consecutiveBadGuesses == 3:
            self.possession = Possession.computer

        if goodAnswer or (self.consecutiveBadGuesses == 3):
            self.consecutiveBadGuesses = 0
            if not goalScored:
                self.possessionLast = possessionLast
                if (self.possession == Possession.human) and (self.possessionLast == Possession.human): #if being passed by human players tell passBall() whom should receive it
                    self.initiatePossessionChange(receivingPlayer)
                else:  #if not being passed by human players execute with no argument
                    self.initiatePossessionChange()

        return goodAnswer

    def destroyPlayerPuzzles(self):
        #Delete old puzzles on players
        if self.possessionLast == Possession.human:
            for x in self.bluePlayers:
                x.destroyPuzzle()

            self.redPlayers[0].destroyPuzzle()
        elif self.possessionLast == Possession.computer:
            self.playerInPossession.destroyPuzzle()

    def initiatePossessionChange(self, receivingPlayer = None):
        goalScored = False
        self.timer_bar.reset()
        self.time_last = time.time()
        self.move_time_left = self.shot_time

        players = list(self.bluePlayers) if self.possession == Possession.human else list(self.redPlayers)
        players.pop(0) #remove goalie

        self.destroyPlayerPuzzles()
        
        #if the ball was previously in the centre, find the nearest player of the receiving team
        if self.possessionLast == Possession.notinposession:
            self.ball.destroyPuzzle()
            (ballx, bally) = self.ball.getPosition()
            self.playerInPossession = self.findNearestPlayer(ballx, bally, players)

        #if a member of the player team is passing to a teammate
        elif self.possessionLast == Possession.human and self.possession == Possession.human:
            self.playerInPossession = receivingPlayer

        #if a member of the computer team is passing to a teammate
        elif self.possessionLast == Possession.computer and self.possession == Possession.computer:
            oldi = self.playerInPossession.getCoords()[0]
            if oldi == 0 or ((oldi == 1) and random.choice([True, False])):     #If in the the first column, or with a 50% chance in the second, score a goal
                #Handle Goal
                goalScored = True
                self.kickGoal("left")   #goal in left goals
            else:   #pass ball forward
                #determine column to pass to
                if oldi == 1:
                    newi = 0
                else:
                    newi = oldi - random.randint(1, 2)

                #find computer players in the target column
                candidates = []
                for x in self.redPlayers:
                    if newi == x.getCoords()[0]:
                        candidates.append(x)

                #randomly pick a recipient from the players in the selected column
                if candidates:
                    self.playerInPossession = random.choice(candidates)
                else: #safety net in case candidate selection above doesn't work
                    self.playerInPossession = self.redPlayers[0]

        #If the ball is being transferred from one team to another
        elif self.possessionLast != self.possession:
            (oldx, oldy) = self.playerInPossession.getPosition()
            (oldi, oldj) = self.playerInPossession.getCoords()
            self.playerInPossession = self.findNearestPlayer(oldx, oldy, players)
            self.playerInPossession.setCoords(oldi, oldj)

        if not goalScored:
            self.playerInPossession.setPosition(*self.field.lookupGridPosition(*self.playerInPossession.getCoords()))
            (newBallx, newBally) = self.playerInPossession.getBallCarryPosition()
            self.ball.setPosition(newBallx,newBally)
            self.ball.move()

            used_positions = 6*[None]
            self.rearrangePlayers("attack", used_positions)
            self.rearrangePlayers("defence", used_positions)

            existingSolutions = []

            if self.possession == Possession.human:
                for x in self.bluePlayers:
                    if x != self.playerInPossession and x != self.bluePlayers[0]:
                        x.generatePuzzle(existingSolutions)
                        existingSolutions.append(x.getPuzzleSolution())

                if self.playerInPossession.getCoords()[0] >= self.gridWidth - 2:
                    self.redPlayers[0].generatePuzzle(existingSolutions)

            elif self.possession == Possession.computer:
                self.playerInPossession.generatePuzzle([])

    def kickGoal(self, side):
        if side == "right": #goal to player
            self.score[0] += 1
            goal_message = "\u00a1GOL DEL JUGADOR!"
            text_colour = "blue"
        elif side == "left": #goal to computer
            self.score[1] += 1
            goal_message = "\u00a1GOL DEL COMPUTADOR!"
            text_colour = "red"

        self.label_score.config(text = str(self.score[0]) + " - " + str(self.score[1]))
        self.ball.setPosition(*self.field.getGoalBallPosition(side))
        self.ball.move()
        self.gameRunning = False

        self.canvas.itemconfig(self.highlight_text, text = goal_message, fill= text_colour, state = tk.NORMAL)
        self.canvas.itemconfig(self.highlight_textbox, state = tk.NORMAL)
        self.canvas.tag_raise(self.highlight_textbox)
        self.canvas.tag_raise(self.highlight_text)
        self.canvas.itemconfig(self.message_text, text = "CLICK PARA CONTINUAR", state = tk.NORMAL)
        self.canvas.itemconfig(self.message_textbox, state = tk.NORMAL)
        self.canvas.tag_raise(self.message_textbox)
        self.canvas.tag_raise(self.message_text)
        self.possessionLast = self.possession
        self.possession = Possession.notinposession

    def rearrangePlayers(self, side, usedPositions):

        #add player in possession to the usedPositions matrix if it's not already there
        (balli, ballj) = self.playerInPossession.getCoords()
        if not usedPositions[balli]:
            usedPositions[balli] = [ballj]
        else:
            if not ballj in usedPositions[balli] : usedPositions[balli].append(ballj)

        #get the list of players to be arranged and remove the goalie. Setup order of processing columns and players based on which team is attacking
        if self.possession == Possession.human:
            if side == "attack":
                players = self.bluePlayers[1:len(self.bluePlayers)]
                team = "human"
            elif side == "defence":
                players = self.redPlayers[1:len(self.redPlayers)]
                team = "computer"
            reverse_flag = False
            start = self.gridWidth - 1
            end = -1
            step = -1
        elif self.possession == Possession.computer:
            if side == "attack":
                players = self.redPlayers[1:len(self.redPlayers)]
                team = "computer"
            elif side == "defence":
                players = self.bluePlayers[1:len(self.bluePlayers)]
                team = "human"
            reverse_flag = True
            start = 0
            end = self.gridWidth
            step = 1

        if side == "attack":    #if it is the attack side remove the player in possession from list of players to be rearranged
            players.remove(self.playerInPossession)

        players.sort(key=lambda Player: Player.i, reverse = reverse_flag)

        for a in range (start, end, step):
            if team == "human":
                (matrixi, matrixj) = (balli, a)
            else:
                (matrixi, matrixj) = (self.gridWidth - balli - 1, self.gridWidth - a - 1)

            if side == "attack":
                playersInColumn = self.attackMatrix[matrixi][matrixj]
            elif side == "defence":
                playersInColumn = self.defenceMatrix[matrixi][matrixj]

            while playersInColumn > 0 and players:
                currentPlayer = players.pop()
                oldj = currentPlayer.getCoords()[1]

                if side == "attack":    #if attacking side, let players new rows be no more than 1 higher or lower than previous
                    if oldj <= 1:
                        possibleRows = [0, 1, 2]
                    elif oldj >= self.gridHeight - 2:
                        possibleRows = [self.gridHeight - 3, self.gridHeight - 2, self.gridHeight - 1]
                    else:
                        possibleRows = [oldj - 1, oldj, oldj + 1]
                elif side == "defence": #if defending side, any row is possible so as not to conflict with attacking side placement
                    possibleRows = list(range(0, self.gridHeight))

                #Take used rows out of list of possible rows for player being placed
                if usedPositions[a]:
                    for x in usedPositions[a]:
                        if x in possibleRows : possibleRows.remove(x)

                if not possibleRows:
                    raise NameError("No rows to place player")

                newj = random.choice(possibleRows)
                if usedPositions[a]:
                    usedPositions[a].append(newj)
                else:
                    usedPositions[a] = [newj]

                currentPlayer.setCoords(a, newj)
                currentPlayer.setPosition(*self.field.lookupGridPosition(a, newj))

                playersInColumn-= 1


        for x in self.bluePlayers:
            x.move()

        for x in self.redPlayers:
            x.move()

    def findNearestPlayer(self, posx, posy, players):
        distanceToNearestPlayer = int(self.canvas.cget("width")) + int(self.canvas.cget("height"))
        for x in players:
            (playerX, playerY) = x.getPosition()
            xdist = abs(posx - playerX)
            ydist = abs(posy - playerY)
            dist = int(pow(pow(xdist, 2) + pow(ydist, 2), 0.5))
            if dist < distanceToNearestPlayer:
                nearestPlayer = x
                distanceToNearestPlayer = dist
        return nearestPlayer

    def createPlayers(self, playerNames, start, pathToPlayerImage, pathToGoalkeeperImage, side):
        numPlayers = len(playerNames)
        players = numPlayers * [None]
        (x, y) = self.field.getGoalkeeperPosition(side)
        players[0] = Player(self.canvas, -1, -1, x, y, playerNames[0], pathToGoalkeeperImage, side)
        for i in range(0, numPlayers - 1):
            (gridi, gridj) = start[i]
            (x, y) = self.field.lookupGridPosition(start[i][0], start[i][1])
            players[i + 1] = Player(self.canvas, start[i][0], start[i][1], x, y, playerNames[i + 1], pathToPlayerImage, side)
        return players

    def getBallInPossession(self):
        return self.ballInPossession

    def setBallInPossession(self, possession):
        self.ballInPossession = possession

    def getGameRunning(self):
        return self.gameRunning

    def setGameRunning(self, running):
        self.gameRunning = running

    def setPaused(self, isPaused):
        if isPaused == False:
            self.time_last = time.time()

        self.paused = isPaused

    def getPaused(self):
        return self.paused

class FieldObject(object):
    __metaclass__ = ABCMeta

    def getPosition(self):
        return (self.x, self.y)

    def setPosition(self, x, y):
        (self.x, self.y) = (x, y)

    def getCoords(self):
        return (self.i, self.j)

    def setCoords(self, i, j):
        (self.i, self.j) = (i, j)

    def getPuzzleSolution(self):
        return self.a + self.b



class Player(FieldObject):
    def __init__(self, canvas, starti, startj, startX, startY, name, imagePath, side):
        self.canvas = canvas
        self.i = starti     #grid column
        self.j = startj     #grid row
        self.x = startX
        self.y = startY
        self.name = name
        self.originalBitmap = Image.open(imagePath)
        self.side = side
        self.puzzleText = ""
        self.wigglePosition = int(0)

        tempWidth, tempHeight = self.originalBitmap.size
        playerHeight = int(int(canvas.cget("height")) * 12 / 100)
        self.bitmap = self.originalBitmap.resize((int(tempWidth / tempHeight * playerHeight), playerHeight), Image.ANTIALIAS)
        (self.width, self.height) = self.bitmap.size
        self.image = ImageTk.PhotoImage(self.bitmap)
        self.canvasImage = canvas.create_image(self.x, self.y, image=self.image)
        if self.name != "":
            self.canvasNameText = canvas.create_text(self.x, int(self.y + self.height/2 + 0.12 * self.height), text=self.name)

    def wiggle(self):
        if self.wigglePosition == 0:
            self.wigglePosition = -2
        elif self.wigglePosition == -2:
            self.wigglePosition = -3
        elif self.wigglePosition == -3:
            self.wigglePosition = -1
        elif self.wigglePosition == -1:
            self.wigglePosition = 1
        elif self.wigglePosition == 1:
            self.wigglePosition = 3
        elif self.wigglePosition == 3:
            self.wigglePosition = 2
        elif self.wigglePosition == 2:
            self.wigglePosition = 0

        self.canvas.coords(self.canvasImage, self.x + self.wigglePosition, self.y)

    def getBallCarryPosition(self):
        if self.side == "left":
            x = int(self.x + self.width / 2)
        elif self.side == "right":
            x = int(self.x - self.width / 2)
        y = int(self.y + self.height / 2)
        return (x, y)

    def generatePuzzle(self, existingSolutions = []):
        uniqueSolution = False
        while uniqueSolution == False: #while the puzzle's solution is not unique
            self.a = random.randint(0, 49) #generate terms
            self.b = random.randint(0, 49)

            matchedOtherSolution = 0
            for x in existingSolutions: #check each existing solution to see if there was a match
                if int(self.a + self.b) == x:
                    matchedOtherSolution = 1

            if matchedOtherSolution == 0: #if solution didn't match any existing ones it is unique
                uniqueSolution = 1

        self.puzzleText = self.canvas.create_text(self.x, int(self.y - self.height/2 - 0.10 * self.height), text=str(self.a) + " + " + str(self.b), font=("Helvetica", "16"),fill="black")

    def move(self):
        self.canvas.coords(self.canvasImage, self.x, self.y)
        self.canvas.coords(self.canvasNameText, self.x, int(self.y + self.height/2 + 0.12 * self.height))

    def destroyPuzzle(self):
        self.canvas.delete(self.puzzleText)

class Ball(FieldObject):
    def __init__(self, canvas, startX, startY, imagePath):
        self.canvas = canvas
        self.x = startX
        self.y = startY
        self.originalBitmap = Image.open(imagePath)
        self.puzzleText = ""

        (tempwidth, tempheight) = self.originalBitmap.size
        ballHeight = int(int(canvas.cget("height")) * 5/ 100)
        self.bitmap = self.originalBitmap.resize((int(tempwidth / tempheight * ballHeight), ballHeight), Image.ANTIALIAS)
        (self.height, self.width) = self.bitmap.size
        self.image = ImageTk.PhotoImage(self.bitmap)
        self.canvasImage = canvas.create_image(self.x, self.y, image=self.image)
        #self.puzzleText = canvas.create_text(self.x, int(self.y - self.height/2 - 0.25 * self.height), text=str(self.a) + " + " + str(self.b), font=("Helvetica", "12"),fill="orange")

    def move(self):
        self.canvas.coords(self.canvasImage, self.x, self.y)

    def generatePuzzle(self):
        self.a = random.randint(0, 49)
        self.b = random.randint(0, 49)
        self.puzzleText = self.canvas.create_text(self.x, int(self.y - self.height/2 - 0.5 * self.height), text=str(self.a) + " + " + str(self.b), font=("Helvetica", "16"),fill="black")
        self.puzzleTextBox = self.canvas.create_rectangle(self.canvas.bbox(self.puzzleText), width=0,  fill="#54ED4E")
        self.canvas.lower(self.puzzleTextBox, self.puzzleText)

    def destroyPuzzle(self):
        self.canvas.delete(self.puzzleTextBox)
        self.canvas.delete(self.puzzleText)

class Field:
    def __init__(self, canvas, gridWidth, gridHeight, fieldCanvasWidthPercentage, goalHeightPercentage, goalSquareWidthPercentage, goalSquareHeightPercentage, goalPostThicknessPercentage, centreCircleSizePercentage, colourField, colourFieldLines, colourGoalPosts):
        self.gridWidth = gridWidth
        self.gridHeight = gridHeight
        self.colour = colourField
        self.width = int(canvas.cget("width"))
        self.height = int(canvas.cget("height"))
        self.leftFieldLineX = int(self.width * (1 - fieldCanvasWidthPercentage/100)/2) # X co-ordinate of left field line
        self.rightFieldLineX = int(self.width * (1 + fieldCanvasWidthPercentage/100)/2) # X co-ordinate of left field line
        self.goalHeight = int(self.height * goalHeightPercentage / 100)
        goalSquareHeight = int(self.height * goalSquareHeightPercentage / 100)
        goalSquareWidth = int(self.width * goalSquareWidthPercentage / 100)
        self.goalPostThickness = int(self.goalHeight * goalPostThicknessPercentage / 100)
        centreCircleSize = int(self.height * centreCircleSizePercentage / 100)

        leftGoalPoints = [2, int(self.height / 2 - self.goalHeight/2), self.leftFieldLineX, int(self.height / 2 - self.goalHeight/2), self.leftFieldLineX, int(self.height / 2 - self.goalHeight/2 + self.goalPostThickness), 2 + self.goalPostThickness, int(self.height / 2 - self.goalHeight/2 + self.goalPostThickness), 2 + self.goalPostThickness, int(self.height / 2 + self.goalHeight/2 - self.goalPostThickness), self.leftFieldLineX, int(self.height / 2 + self.goalHeight/2 - self.goalPostThickness), self.leftFieldLineX, int(self.height / 2 + self.goalHeight/2), 2, int(self.height / 2 + self.goalHeight/2), 2, int(self.height / 2 - self.goalHeight/2)]
        rightGoalPoints = [self.width, int(self.height / 2 - self.goalHeight/2), self.rightFieldLineX, int(self.height / 2 - self.goalHeight/2), self.rightFieldLineX, int(self.height / 2 - self.goalHeight/2 + self.goalPostThickness), self.width - self.goalPostThickness, int(self.height / 2 - self.goalHeight/2 + self.goalPostThickness), self.width - self.goalPostThickness, int(self.height / 2 + self.goalHeight/2 - self.goalPostThickness), self.rightFieldLineX, int(self.height / 2 + self.goalHeight/2 - self.goalPostThickness), self.rightFieldLineX, int(self.height / 2 + self.goalHeight/2), self.width, int(self.height / 2 + self.goalHeight/2), self.width, int(self.height / 2 - self.goalHeight/2)]

        self.fieldOutline = canvas.create_rectangle(self.leftFieldLineX, 2, self.rightFieldLineX, self.height, fill=colourField , outline=colourFieldLines, width=2) #draw field
        self.centreCircle = canvas.create_oval(int(self.width / 2) - int( centreCircleSize / 2), int(self.height / 2) - int(centreCircleSize / 2), int(self.width / 2) + int( centreCircleSize / 2), int(self.height / 2) + int( centreCircleSize / 2), outline=colourFieldLines, width=2) #draw centre circle
        self.midFieldLine = canvas.create_line(int (self.width / 2), 0, int (self.width / 2), self.height, fill=colourFieldLines, width=2) #draw midfield line
        self.leftGoalSquare = canvas.create_rectangle(self.leftFieldLineX, int(self.height / 2) - int(goalSquareHeight/2), self.leftFieldLineX + goalSquareWidth, int(self.height / 2) + int(goalSquareHeight/2),outline=colourFieldLines,  width=2) #draw left goal square
        self.leftGoalSquare = canvas.create_rectangle(self.rightFieldLineX, int(self.height / 2) - int(goalSquareHeight/2), self.rightFieldLineX - goalSquareWidth, int(self.height / 2) + int(goalSquareHeight/2),outline=colourFieldLines,  width=2) #draw left goal square
        self.leftGoal = canvas.create_polygon(leftGoalPoints, outline = colourFieldLines, fill=colourGoalPosts, width=2) #draw left goal
        self.rightGoal = canvas.rightGoal = canvas.create_polygon(rightGoalPoints, outline = colourFieldLines, fill=colourGoalPosts, width=2) #draw right goal

    def lookupGridPosition(self, i, j):
        x = self.leftFieldLineX + int((self.rightFieldLineX - self.leftFieldLineX) * ((0.5 + i) / self.gridWidth))
        y = int(self.height * (0.5 + j) / self.gridHeight)
        return (x, y)

    def getColour(self):
        return self.colour

    def getCentreFieldPosition(self):
        return (int(self.leftFieldLineX + (self.rightFieldLineX - self.leftFieldLineX)/2), int(self.height / 2))

    def getGoalBallPosition(self, side):
        ymod = int(0.35 * self.goalHeight * random.choice([-1, 1]))
        if side == "left":
            return (int(self.leftFieldLineX *0.35), int(self.height / 2 + ymod))
        elif side == "right":
            return (int(self.rightFieldLineX + 0.65 * (self.width - self.rightFieldLineX)), int(self.height / 2 + ymod))

    def getGoalkeeperPosition(self, side):
        if side == "left":
            (x, y) = (int(self.goalPostThickness + (self.leftFieldLineX - self.goalPostThickness) * 2/3), self.height / 2)
        elif side == "right":
            (x, y) = (int(self.rightFieldLineX + (self.width - self.goalPostThickness - self.rightFieldLineX) * 1/3), self.height / 2)
        else:
            raise NameError ('side must be "left" or "right')
        return (x, y)

class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.pack()
        self.createWidgets()
        self.createGame()

    def createWidgets(self):
        field_width = 1200
        field_height = 600
        colourBackground = "#FBFBFB"

        self.mframe = tk.Frame(self, relief="flat", bd=3, background="white")
        self.mframe.pack(side="top")
        self.mframe.columnconfigure(0, weight=1)
        self.mframe.columnconfigure(1, weight=1)
        self.mframe.columnconfigure(2, weight=1)
        self.mframe.columnconfigure(3, weight=1)
        self.mframe.columnconfigure(4, weight=1)

        self.canvas = tk.Canvas(self.mframe, height=field_height, width=field_width, background=colourBackground)
        self.canvas.pack(side="top")
        self.canvas.bind("<Button-1>", self.handleCanvasClick)

        self.canvas.grid(row=0,columnspan=5)

        #self.update()

        self.timer_canvas = tk.Canvas(self.mframe, height=int(field_height / 35), width=field_width)
        self.timer_canvas.grid(row=1,columnspan=5)
        self.timer_rectangle = self.timer_canvas.create_rectangle(1,1, int(self.timer_canvas.cget("width")) - 0, int(self.timer_canvas.cget("height")) - 0, fill="#00FF00", outline="black", width=1)
        self.timer = TimerBar(self.timer_canvas, self.timer_rectangle)

        #self.bframe = tk.Frame(self, relief="flat", bd=5)
        #self.bframe.pack(side="top")

        self.time = tk.Label(self.mframe, text="2:00", font=("Arial, 32"), relief="sunken", bd=2, width=1)
        #self.time.pack(side="left", fill=tk.Y, padx=2)
        self.time.grid(row=2,column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=2)

        self.score = tk.Label(self.mframe, text="0 - 0", font=("Arial, 32"),  relief="sunken", bd=2, width=1)
        #self.score.pack(side="left", fill=tk.Y, padx=2)
        self.score.grid(row=2,column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=2)

        self.text = tk.Entry(self.mframe,font=("Helvetica",36), justify="center", width=1, state="disabled")
        self.text.focus()
        self.text.bind("<Return>",self.textReturnHandler)
        #self.text.pack(side="left", fill=tk.Y, padx=2)
        self.text.grid(row=2,column=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=2)

        self.frameResults = tk.Frame(self.mframe, background="black", bd=1)
        self.frameResults.grid(row=2,column=3, sticky=tk.W+tk.E+tk.N+tk.S, padx=2)

        numLastResults = 3
        self.labelsLastResults = numLastResults * [None]
        for i in range(0, numLastResults):
            self.labelsLastResults[i] = tk.Label(self.frameResults, text='\u2713', font=("System", "20"), background="white", fg="white", width=1)
            self.labelsLastResults[i].pack(side="left",padx=1, expand=1, fill="both")

        self.buttonPlayPause = tk.Button(self.mframe, text="Pause", state='disabled')
        self.buttonPlayPause.bind("<Button-1>", self.handlePauseButtonClick)
        #self.buttonPlayPause.pack(side="left", fill=tk.BOTH, padx=2)
        self.buttonPlayPause.grid(row=2,column=4, sticky=tk.W+tk.E+tk.N+tk.S, padx=2)

    def createGame(self):
        #Field Setup Data
        fieldSetup = [85,           #Percentage of canvas width to use for field
                      30,           #Goal Height as a percentage of canvas height
                      12,           #Goal Square Width as a percentage of canvas width
                      40,           #Goal Squre Height as a percentage of canvas height
                      5,            #Goal Squre Post Thickness as a percentage of goal square height
                      14,           #Centre circle diameter as a percentage of canvas height
                      "#54ED4E",    #Field Colour
                      "#444444",    #Field Lines Colour
                      "#CCCCCC"]    #Goal Post Colour

        #Player Setup Data
        
        bluePlayerNames = ["Israel", "Luis Angel", "Roberto Carlos", "Moises", "Miguel", "Rafael", "Daniel"]
        redPlayerNames = 7 * [None]

        #Setup Images
        pathToBluePlayerImage = os.path.join("Images", "BluePlayer.png")
        pathToBlueGoalkeeperImage = os.path.join("Images", "BlueGoalkeeper.png")
        pathToRedPlayerImage = os.path.join("Images", "RedPlayer.png")
        pathToRedGoalkeeperImage = os.path.join("Images", "RedGoalkeeper.png")
        pathToBallImage = os.path.join("Images", "Ball.png")

        #Create Game Tracker
        self.game = GameTracker(self.canvas, self.timer, self.time, self.score, fieldSetup, bluePlayerNames, redPlayerNames, pathToBluePlayerImage, pathToBlueGoalkeeperImage, pathToRedPlayerImage, pathToRedGoalkeeperImage, pathToBallImage)

    def handleCanvasClick(self, event):
        self.buttonPlayPause.config(state='normal')
        self.text.config(state='normal')
        if self.game.getGameRunning() == 0:
            self.game.startPlay()

    def textReturnHandler(self, event):
        entryText = self.text.get()  #get contents of entry cell
        if entryText !=  "" and self.game.getPaused() == False:
            goodAnswer = self.game.handleUserInput(int(entryText))

            #first 2 most recent results one to the right
            for i in range(2, 0, -1):
                self.labelsLastResults[i].configure(text=self.labelsLastResults[i-1].cget("text"), fg=self.labelsLastResults[i-1].cget("fg"))

            if goodAnswer == True:
                newtext = '\u2713'
                newfg = "green"
            else:
                newtext = '\u2718'
                newfg = "red"

            self.labelsLastResults[0].configure(text=newtext, fg=newfg)

        self.text.delete(0, tk.END)

    def poll(self):
        self.game.update()
        self.after(20, self.poll)

    def handlePauseButtonClick(self, event):
        if self.game.getPaused(): #if paused
            self.buttonPlayPause.config(text="Pause")
            self.game.setPaused(False)
        else: #if not paused
            self.buttonPlayPause.config(text="Resume")
            self.game.setPaused(True)

root = tk.Tk()
root.wm_title("Math Ball")
w = str(int(0.95 * root.winfo_screenwidth()))
h = str(int(0.95 * root.winfo_screenheight()))
root.geometry(w + "x" + h + "+0+0")
#root.attributes('-zoomed', True)

app = Application(master=root)
pollid = app.after(20, app.poll)
app.mainloop()
