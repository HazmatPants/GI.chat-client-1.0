from tkinter import messagebox 
import tkinter as tk # for GUI

from ping3 import ping # for pinging the server
import time # for timestamps
import asyncio # for async functions
import websockets # for communication with the server
import threading # for running multiple functions at once
import json # for sending multiple values to the server
from pygame import mixer

mixer.init()

def playsound(sound: str):
    mixer.Sound(sound).play()

def playeventsound(event: str):
    if event == "send_message":
        playsound("sounds/send.wav")
    elif event == "rcv_message":
        playsound("sounds/receive.wav")
    elif event == "connected":
        playsound("sounds/join.wav")
    elif event == "srv_message":
        playsound("sounds/server_message.wav")

username="HazmatPants"

# Initialize Tkinter
root = tk.Tk()
root.title("GIchat Client 1.1")
root.geometry("400x300")
root.grid_columnconfigure(1, weight=1)  # Allow text widget to expand
root.grid_rowconfigure(0, weight=1)     # Allow window resizing
root.configure(bg="black")

# Global Variables
websocket = None
loop = None
asyncio_thread = None
shutdown_flag = False # if this is true, program and threads will shutdown

host = "192.168.1.195"
port = 8765

# Function to print messages to the text console
def consoleprint(text: str):
    def updateconsole():
        text_console.config(state=tk.NORMAL)
        text_console.insert(tk.END, text + "\n")
        text_console.config(state=tk.DISABLED)
    
    root.after(0, updateconsole)

# Function to ping the server
def pingserver() -> float:
    responsetime = ping(dest_addr=host)
    if responsetime is None or responsetime is False:
        consoleprint("Ping Failed")
        messagebox.showerror(title="Ping Failed", message="Host unreachable")
    else:
        consoleprint(f"Ping Success: {str(round(responsetime, 3) * 100)}ms")
        print("ping success:", responsetime)
        messagebox.showinfo(title="Ping Sucessful", message="Response Time: " + str(round(responsetime, 3) * 100) + "ms")

def disconnect():
    global shutdown_flag, websocket
    shutdown_flag = True
    if websocket:
        websocket.close()
    
    root.quit()
    exit()
    
root.protocol("WM_DELETE_WINDOW", disconnect)

# Menu bar for the app
menubar = tk.Menu(root)
root.config(menu=menubar)

# Show credits window
def showcredits():
    messagebox.showinfo(title="Credits", message="Made by Grigga Industries\nMade in Python 3.10")

menu_info = tk.Menu(menubar, tearoff=0)
menu_info.add_command(label="Credits", command=showcredits)
menu_info.add_command(label="Exit", command=exit)
menubar.add_cascade(label="Options", menu=menu_info)

# Frame to hold buttons
frame_button = tk.Frame(root, bg="black")
frame_button.grid(row=0, column=0, padx=5, pady=5, sticky="ns")

button_ping = tk.Button(frame_button, text="Ping", width=5, bg="#232323", fg="#ffffff", command=pingserver)

# Received messages and errors go to the text console
text_console = tk.Text(root, width=30, height=10, bg="#232323", fg="#ffffff")

button_ping.pack()

# test button to see if layout works
button_test1 = tk.Button(frame_button, text="test", width=5, bg="#232323", fg="#ffffff")
button_test1.pack()

text_console.grid(row=0, column=1, pady=5, columnspan=2, sticky="nsew")
text_console.config(state=tk.DISABLED)

messagefield = tk.Text(root, bg="#232323", fg="#ffffff", height=2)
messagefield.grid(row=3, column=1, columnspan=1, pady=5, sticky="ew")

# Function to send the message
async def sendmessage():
    global websocket
    message = messagefield.get("1.0", tk.END)  # Get the message from the field
    messagefield.delete("1.0", tk.END)
    if message:
        message_data = {
            "username": username,
            "message": message,
            "event": "send_message"
            }
        
        message_json = json.dumps(message_data)
        
        timestamp = time.time()
        
        await websocket.send(message_json)  # Send the message over WebSocket
        playeventsound("send_message")
        root.after(0, consoleprint, f"{username} (You): {message}")
        print(f"Sent {message.strip()} at {timestamp:.4f}")

# Function to handle receiving messages
async def receive_messages():
    global websocket
    try:
        async for message in websocket:
            try:
                message_data = json.loads(message)
                print(f"Received data: {message_data}")
            except json.JSONDecodeError:
                consoleprint("Received invalid data: " + message)
            if message_data["event"] == "srv_message":
                playeventsound("srv_message")
                consoleprint(message_data["username"] + ": " + message_data["message"])
            elif message_data["event"] == "send_message":
                playeventsound("send_message")
                consoleprint(message_data["username"] + ": " + message_data["message"])
    except websockets.exceptions.ConnectionClosed:
        consoleprint("Connection to server closed")

# Connect to the WebSocket server
async def connect():
    global websocket
    global username
    uri = "ws://" + host + ":" + str(port)  # Change this to your server's address if needed
    websocket = await websockets.connect(uri)
    
    await websocket.send(username)
    
    consoleprint(f"Connected to {uri}")
    playeventsound("connected")
    await receive_messages()

# Tkinter button command to send messages
def send_button_click():
    global loop
    if loop:
        asyncio.run_coroutine_threadsafe(sendmessage(), loop)
    else:
        print("No event loop")

# Start the WebSocket connection in the background
def start_asyncio_loop():
    global loop
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)  # Set it as the current event loop
    try:
        loop.run_until_complete(connect())  # Start the connection
    except ConnectionRefusedError:
        tk.messagebox.showerror(title="Failed to connect...", message="Error: Connection Refused")
        disconnect()
    while not shutdown_flag:
        loop.run_forever()  # Keep the loop running

# Add button to send message
button_send = tk.Button(root, width=5, text="Send", bg="#232323", fg="#ffffff", command=send_button_click)
button_send.grid(row=3, column=2)

# Start the asyncio event loop in a separate thread to avoid blocking Tkinter
asyncio_thread = threading.Thread(target=start_asyncio_loop, daemon=True)
asyncio_thread.start()

root.mainloop()