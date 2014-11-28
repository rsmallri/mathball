__author__ = 'ryan'

import tkinter as tk
import os
from PIL import Image, ImageTk
import random
from enum import Enum

class Possession(Enum):
    notinposession = 1
    human = 2
    computer = 3

class GameTracker:
    def __init__(self, canvas, fieldSetup, startPositionsBlue, bluePlayerNames, startPositionsRed, redPlayerNames, pathToBluePlayerImage, pathToBlueGoalkeeperImage, pathToRedPlayerImage, pathToRedGoalkeeperImage, pathToBallImage):
        self.canvas = canvas

        self.attackMatrix = [[2,2,1,0,0,0],[1,1,2,1,0,0],[0,2,1,1,1,0],[0,1,1,1,1,1],[0,0,1,1,1,2],[0,0,0,1,2,2]]
        self.defenceMatrix = [[2,2,1,1,0,0],[1,2,2,1,0,0],[0,1,2,2,1,0],[0,0,1,2,2,1],[0,0,0,2,2,2],[0,0,0,1,3,2]]

        self.gridWidth = 6
        self.gridHeight = 5
        self.possession = Possession.notinposession
        self.gameRunning = 0
        self.paused = 0
        self.consecutiveBadGuesses = 0

        #create Field
        self.field = Field(self.canvas, self.gridWidth, self.gridHeight, *fieldSetup)#fieldSetup[0], fieldSetup[1], fieldSetup[2], fieldSetup[3], fieldSetup[4], fieldSetup[5], fieldSetup[6], fieldSetup[7], fieldSetup[8])

        #Create Players
        self.bluePlayers = self.createPlayers(bluePlayerNames, startPositionsBlue, pathToBluePlayerImage, pathToBlueGoalkeeperImage, "left")
        self.numBluePlayers = len(self.bluePlayers)
        self.redPlayers = self.createPlayers(redPlayerNames, startPositionsRed, pathToRedPlayerImage, pathToRedGoalkeeperImage, "right")
        self.numRedPlayers = len(self.redPlayers)

        #create Ball
        (ballStartX, ballStartY) = self.field.getCentreFieldPosition()
        self.ball = Ball(self.canvas, ballStartX, ballStartY, pathToBallImage)

        self.enterToStartText = self.canvas.create_text(int(int(self.canvas.cget("width"))/ 2), int(int(self.canvas.cget("height")) * 0.4), text="CLICK PARA COMENZAR", font=("Helvetica", "20"), fill="blue")
        self.enterToStartTextBox = self.canvas.create_rectangle(self.canvas.bbox(self.enterToStartText), width=0,  fill="#87FA89")
        self.canvas.lower(self.enterToStartTextBox, self.enterToStartText)


    def startGame(self):
        self.gameRunning = True
        self.canvas.delete(self.enterToStartText)
        self.canvas.delete(self.enterToStartTextBox)
        self.ball.generatePuzzle()
        #add code for timers

    def wigglePlayers(self):
        if self.gameRunning == True and self.paused == False:
            for x in self.bluePlayers:
                x.wiggle()
            for x in self.redPlayers:
                x.wiggle()

    def handleUserInput(self, inputNumber):
        goodAnswer = False
        possessionLast = self.possession
        if self.possession == Possession.notinposession: #No player has possession
            if inputNumber == self.ball.getPuzzleSolution():
                goodAnswer = True

        elif self.possession == Possession.human: #human in possession
            for x in self.bluePlayers:
                if x != self.playerInPossession:
                    if inputNumber == x.getPuzzleSolution():
                        goodAnswer = True
                        receivingPlayer = x
                        break

        elif self.possession == Possession.computer: #computer in possession
            if inputNumber == self.playerInPossession.getPuzzleSolution():
                goodAnswer = True

        if goodAnswer:
            self.possession = Possession.human
        else:
            self.consecutiveBadGuesses += 1

        if self.consecutiveBadGuesses == 3:
            self.possession = Possession.computer

        if goodAnswer or (self.consecutiveBadGuesses == 3):
            self.consecutiveBadGuesses = 0
            self.possessionLast = possessionLast
            if (self.possession == Possession.human) and (self.possessionLast == Possession.human): #if being passed by human players tell passBall() whom should receive it
                self.initiatePossessionChange(receivingPlayer)
            else:  #if not being passed by human players execute with no argument
                self.initiatePossessionChange()

        return goodAnswer


    def initiatePossessionChange(self, receivingPlayer = None):
        players = self.bluePlayers if self.possession == Possession.human else self.redPlayers

        #Delete old puzzles on players
        if self.possessionLast == Possession.human:
            for x in self.bluePlayers:
                x.destroyPuzzle()
        elif self.possessionLast == Possession.computer:
            self.playerInPossession.destroyPuzzle()

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
            if oldi == 0 or ((oldi == 1) and random.choice(True, False)):     #If in the the first column, or with a 50% chance in the second, score a goal
                #Handle Goal
                print("goal to computer")
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

        (newBallx, newBally) = self.playerInPossession.getBallCarryPosition()

        self.ball.moveTo(newBallx, newBally)

        #Re-arrange players not in possession
        if self.possession == Possession.human:
            for a in range (self.gridWidth, 0, - 1):
                playersInColumn = self.attackMatrix[a][newi]
                while playersInColumn > 0:




        if self.possession == Possession.human:
            existingSolutions = []
            for x in self.bluePlayers:
                if x != self.playerInPossession: #for players not in possession
                    x.generatePuzzle(existingSolutions)
                    existingSolutions.append(x.getPuzzleSolution())

        elif self.possession == Possession.computer:
            self.playerInPossession.generatePuzzle()





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
        self.paused = isPaused

    def getPaused(self):
        return self.paused

class Player:
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
        playerHeight = int(int(canvas.cget("height")) * 13 / 100)
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
        uniqueSolution = 0
        while uniqueSolution == 0: #while the puzzle's solution is not unique
            self.a = random.randint(0, 49) #generate terms
            self.b = random.randint(0, 49)

            matchedOtherSolution = 0
            for x in existingSolutions: #check each existing solution to see if there was a match
                if int(self.a + self.b) == x:
                    matchedOtherSolution = 1

            if matchedOtherSolution == 0: #if solution didn't match any existing ones it is unique
                uniqueSolution = 1

        self.puzzleText = self.canvas.create_text(self.x, int(self.y - self.height/2 - 0.10 * self.height), text=str(self.a) + " + " + str(self.b), font=("Helvetica", "16"),fill="black")


    def getPosition(self):
        return (self.x, self.y)

    def getCoords(self):
        return (self.i, self.j)

    def setCoords(self, i, j):
        (self.i, self.j) = (i, j)

    def getPuzzleSolution(self):
        return self.a + self.b

    #def moveTo(self, newX, newY):
        #To be completed

    def destroyPuzzle(self):
        self.canvas.delete(self.puzzleText)
        self.a = -1
        self.b = -1

class Ball:
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

    def moveTo(self, newX, newY):
        self.canvas.coords(self.canvasImage, newX, newY)

    def getPosition(self):
        return (self.x, self.y)

    def generatePuzzle(self):
        self.a = random.randint(0, 49)
        self.b = random.randint(0, 49)
        self.puzzleText = self.canvas.create_text(self.x, int(self.y - self.height/2 - 0.5 * self.height), text=str(self.a) + " + " + str(self.b), font=("Helvetica", "16"),fill="black")
        self.puzzleTextBox = self.canvas.create_rectangle(self.canvas.bbox(self.puzzleText), width=0,  fill="#87FA89")
        self.canvas.lower(self.puzzleTextBox, self.puzzleText)

    def getPuzzleSolution(self):
        return self.a + self.b
        self.a = -1
        self.b = -1

    def destroyPuzzle(self):
        self.canvas.delete(self.puzzleTextBox)
        self.canvas.delete(self.puzzleText)

class Field:
    def __init__(self, canvas, gridWidth, gridHeight, fieldCanvasWidthPercentage, goalHeightPercentage, goalSquareWidthPercentage, goalSquareHeightPercentage, goalPostThicknessPercentage, centreCircleSizePercentage, colourField, colourFieldLines, colourGoalPosts):
        self.gridWidth = gridWidth
        self.gridHeight = gridHeight
        self.width = int(canvas.cget("width"))
        self.height = int(canvas.cget("height"))
        self.leftFieldLineX = int(self.width * (1 - fieldCanvasWidthPercentage/100)/2) # X co-ordinate of left field line
        self.rightFieldLineX = int(self.width * (1 + fieldCanvasWidthPercentage/100)/2) # X co-ordinate of left field line
        goalHeight = int(self.height * goalHeightPercentage / 100)
        goalSquareHeight = int(self.height * goalSquareHeightPercentage / 100)
        goalSquareWidth = int(self.width * goalSquareWidthPercentage / 100)
        self.goalPostThickness = int(goalHeight * goalPostThicknessPercentage / 100)
        centreCircleSize = int(self.height * centreCircleSizePercentage / 100)

        leftGoalPoints = [2, int(self.height / 2 - goalHeight/2), self.leftFieldLineX, int(self.height / 2 - goalHeight/2), self.leftFieldLineX, int(self.height / 2 - goalHeight/2 + self.goalPostThickness), 2 + self.goalPostThickness, int(self.height / 2 - goalHeight/2 + self.goalPostThickness), 2 + self.goalPostThickness, int(self.height / 2 + goalHeight/2 - self.goalPostThickness), self.leftFieldLineX, int(self.height / 2 + goalHeight/2 - self.goalPostThickness), self.leftFieldLineX, int(self.height / 2 + goalHeight/2), 2, int(self.height / 2 + goalHeight/2), 2, int(self.height / 2 - goalHeight/2)]
        rightGoalPoints = [self.width, int(self.height / 2 - goalHeight/2), self.rightFieldLineX, int(self.height / 2 - goalHeight/2), self.rightFieldLineX, int(self.height / 2 - goalHeight/2 + self.goalPostThickness), self.width - self.goalPostThickness, int(self.height / 2 - goalHeight/2 + self.goalPostThickness), self.width - self.goalPostThickness, int(self.height / 2 + goalHeight/2 - self.goalPostThickness), self.rightFieldLineX, int(self.height / 2 + goalHeight/2 - self.goalPostThickness), self.rightFieldLineX, int(self.height / 2 + goalHeight/2), self.width, int(self.height / 2 + goalHeight/2), self.width, int(self.height / 2 - goalHeight/2)]

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
    
    def getCentreFieldPosition(self):
        return (int(self.leftFieldLineX + (self.rightFieldLineX - self.leftFieldLineX)/2), int(self.height / 2))

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
        canvas_width = 1200
        canvas_height = 600
        colourBackground = "#FBFBFB"

        self.mframe = tk.Frame(self, relief="flat", bd=3, background="white")
        self.mframe.pack(side="top")

        self.canvas = tk.Canvas(self.mframe, height=canvas_height, width=canvas_width, background=colourBackground)
        self.canvas.pack(side="top")
        self.canvas.bind("<Button-1>", self.handleCanvasClick)

        self.bframe = tk.Frame(self, relief="flat", bd=8)
        self.bframe.pack(side="bottom")

        self.time = tk.Label(self.bframe, text="2:00", font=("Arial, 32"), relief="sunken", width=8, bd=2)
        self.time.pack(side="left", fill=tk.Y, padx=2)

        self.score = tk.Label(self.bframe, text="0 - 0", font=("Arial, 32"),  relief="sunken", width=8, bd=2)
        self.score.pack(side="left", fill=tk.Y, padx=2)

        self.text = tk.Entry(self.bframe,font=("Helvetica",48), justify="center", width = 8)
        self.text.focus()
        self.text.bind("<Return>",self.textReturnHandler)
        self.text.pack(side="left", fill=tk.Y, padx=2)

        self.frameResults = tk.Frame(self.bframe, background="black", bd=1)
        self.frameResults.pack(side="left", fill=tk.Y)

        numLastResults = 3
        self.labelsLastResults = numLastResults * [None]
        for i in range(0, numLastResults):
            self.labelsLastResults[i] = tk.Label(self.frameResults, text='\u2713', font=("System", "50"), background="white", fg="white")
            self.labelsLastResults[i] = tk.Label(self.frameResults, text='\u2713', font=("System", "50"), background="white", fg="white")
            self.labelsLastResults[i].pack(side="left", padx=1, pady=1)

        self.buttonPlayPause = tk.Button(self.bframe, text="Pause", width = 50, state='disabled')
        self.buttonPlayPause.bind("<Button-1>", self.handlePauseButtonClick)
        self.buttonPlayPause.pack(side="left", fill=tk.BOTH, padx=2)


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
        startPositionsBlue = [[0, 2], [1, 1], [1, 3], [2, 0], [2, 2], [2, 4]]
        bluePlayerNames = ["Israel", "Luis Angel", "Roberto Carlos", "Moises", "Miguel", "Rafael", "Daniel"]

        startPositionsRed = [[3, 0], [3, 2], [3, 4], [4, 1], [4, 3], [5, 2]]
        redPlayerNames = 7 * [None]

        #Setup Images
        pathToBluePlayerImage = os.path.join("Images", "BluePlayer.png")
        pathToBlueGoalkeeperImage = os.path.join("Images", "BlueGoalkeeper.png")
        pathToRedPlayerImage = os.path.join("Images", "RedPlayer.png")
        pathToRedGoalkeeperImage = os.path.join("Images", "RedGoalkeeper.png")
        pathToBallImage = os.path.join("Images", "Ball.png")

        #Create Game Tracker
        self.game = GameTracker(self.canvas, fieldSetup, startPositionsBlue, bluePlayerNames, startPositionsRed, redPlayerNames, pathToBluePlayerImage, pathToBlueGoalkeeperImage, pathToRedPlayerImage, pathToRedGoalkeeperImage, pathToBallImage)


    def handleCanvasClick(self, event):
        self.buttonPlayPause.config(state='normal')
        if self.game.getGameRunning() == 0:
            self.game.startGame()



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
        self.game.wigglePlayers()
        self.after(100, self.poll)

    def handlePauseButtonClick(self, event):
        if self.game.getPaused(): #if paused
            self.buttonPlayPause.config(text="Pause")
            self.game.setPaused(False)
        else: #if not paused
            self.buttonPlayPause.config(text="Resume")
            self.game.setPaused(True)

root = tk.Tk()
root.wm_title("Math Ball")
w = str(int(0.9 * root.winfo_screenwidth()))
h = str(int(0.9 * root.winfo_screenheight()))
root.geometry(w + "x" + h + "+0+0")
#root.attributes('-zoomed', True)

app = Application(master=root)
pollid = app.after(100, app.poll)
app.mainloop()


