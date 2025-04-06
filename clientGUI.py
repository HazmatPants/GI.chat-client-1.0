from tkinter import messagebox, filedialog, ttk
import tkinter as tk # for GUI

from PIL import Image, ImageTk
from ping3 import ping # for pinging the server
from datetime import datetime
import time # for timestamps
import asyncio # for async functions
import websockets # for communication with the server
import threading # for running multiple functions at once
import json # for sending multiple values to the server
import os # for force-exit
import random # for random numbers
from pygame import mixer # for sound effects
import base64 # for encoding image data
import toml # for config files

mixer.init()

with open("latest.log", "w") as f:
        f.write("")

def b64encode(path):
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
        return encoded

def b64decode(b64string: str):
    return base64.b64decode(b64string)

def log(text: str):
    print(text)
    with open("latest.log", "a") as f:
        f.writelines(text + "\n")

def save_config(data: dict):
    with open("config.toml", "w") as f:
        toml.dump(data, f)

def load_config() -> dict:
    try:
        data = toml.loads(open("config.toml", "r").read())
        log("Config Loaded")
        return data
    except toml.TomlDecodeError:
        log("Invalid Config TOML")
        messagebox.showerror(title="TOML Decode Error", message="Config contains invalid TOML, please check for any mistakes in config.toml or delete it to generate a new config file")
        os._exit(0)
    except FileNotFoundError:
        log("Config file missing")
        data = {
            "client": {
                "username": f"NewUser_{str(random.randint(1,10000))}",
                "font": {
                    "name": "Helvetica",
                    "size": 10
                    },
                "admin_key": ""
            },
            "server": {
                "host": "86.3.132.254",
                "port": 8765,
            }
        }
        
        save_config(data)
        
        messagebox.showerror(title="No Config?", message="Config file is missing, please edit the newly created config.toml")
        
        os._exit(0)

formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
log(f"// {formatted_time} //")

CLI_VERSION = "1.4.1"
CLI_CONFIG = load_config()
CLI_DIR = os.path.dirname(__file__)
os.chdir(CLI_DIR)

def playsound(sound: str):
    mixer.Sound(sound).play()

def playeventsound(event: str):
    sound = "assets/sounds/" + event + ".wav"
    playsound(sound)

host = CLI_CONFIG["server"]["host"]
port = CLI_CONFIG["server"]["port"]
username = CLI_CONFIG["client"]["username"]

# Initialize Tkinter
root = tk.Tk()
root.title(f"GIchat Client {CLI_VERSION}")
root.geometry("900x500")
root.grid_columnconfigure(1, weight=1)  # Allow text widget to expand
root.grid_rowconfigure(0, weight=1)     # Allow window resizing
root.configure(bg="black")
log("Tkinter Initialized")

# Global Variables
websocket = None
loop = None
asyncio_thread = None
shutdown_flag = False # if this is True, program and threads will shutdown

def open_config():
    window = tk.Toplevel(root)
    window.title("Config")
    window.geometry("300x300")
    window.configure(bg="black")
    window.attributes("-topmost", True)
    window.resizable(False, False)
    
    label_host = tk.Label(window, text="Host (IP)", bg="black", fg="#ffffff")
    entry_host = tk.Entry(window, bg="#232323", fg="#ffffff")
    label_port = tk.Label(window, text="Port", bg="black", fg="#ffffff")
    entry_port = tk.Entry(window, bg="#232323", fg="#ffffff")
    label_name = tk.Label(window, text="Username", bg="black", fg="#ffffff")
    entry_name = tk.Entry(window, bg="#232323", fg="#ffffff")
    label_font_name = tk.Label(window, text="Font Name", bg="black", fg="#ffffff")
    entry_font_name = tk.Entry(window, bg="#232323", fg="#ffffff")
    label_font_size = tk.Label(window, text="Font Size", bg="black", fg="#ffffff")
    entry_font_size = tk.Entry(window, bg="#232323", fg="#ffffff")
    label_admin_key = tk.Label(window, text="Admin Key", bg="black", fg="#ffffff")
    entry_admin_key = tk.Entry(window, bg="#232323", fg="#ffffff", show="*")  # Hide key input

    # load current config into entries
    entry_host.insert(0, CLI_CONFIG["server"]["host"])
    entry_port.insert(0, CLI_CONFIG["server"]["port"])
    entry_name.insert(0, CLI_CONFIG["client"]["username"])
    entry_font_name.insert(0, CLI_CONFIG["client"]["font"]["name"])
    entry_font_size.insert(0, CLI_CONFIG["client"]["font"]["size"])
    entry_admin_key.insert(0, CLI_CONFIG["client"]["admin_key"])
    
    def save_user_config():
        data = {
            "client": {
                "username": str(entry_name.get().strip()),
                "font": {
                    "name": str(entry_font_name.get().strip()),
                    "size": int(entry_font_size.get().strip())
                    },
                "admin_key": str(entry_admin_key.get().strip())
            },
            "server": {
                "host": str(entry_host.get().strip()),
                "port": int(entry_port.get().strip()),
            }
        }

        save_config(data)
        messagebox.showinfo(title="Saved Config", message="Config was successfully saved\nA restart is required for changes to apply.")
        asyncio.run_coroutine_threadsafe(client_exit(), loop)
    
    button_save = tk.Button(window, text="Save", width=8, bg="#232323", fg="#ffffff",
                            command=save_user_config)
    
    label_host.pack()
    entry_host.pack()
    label_port.pack()
    entry_port.pack()
    label_name.pack()
    entry_name.pack()
    label_font_name.pack()
    entry_font_name.pack()
    label_font_size.pack()
    entry_font_size.pack()
    label_admin_key.pack()
    entry_admin_key.pack()
    
    button_save.pack(pady=16)

# Function to print messages to the text console
def consoleprint(text: str, image: tk.PhotoImage=None):
    text = text.strip()
    def updateconsole():
        text_console.config(state=tk.NORMAL)
        text_console.insert(tk.END, text + "\n")
        if image:
            text_console.image_create(tk.END, image=image)
            text_console.insert(tk.END, "\n")
        text_console.update()
        text_console.config(state=tk.DISABLED)
    
    root.after(0, updateconsole)
    text_console.see(tk.END)

def load_messages(messages):
    window = tk.Toplevel(root)
    window.title("Loading...")
    window.geometry("350x150")
    window.configure(bg="black")
    window.attributes("-topmost", True)
    window.resizable(False, False) 
    window.grab_set()
    loading_label = tk.Label(window, text="Loading Messages", bg="#000000", fg="#ffffff")
    loading_label.pack(pady=10)
    progress_bar = ttk.Progressbar(window, length=300, mode="determinate")
    progress_bar['maximum'] = len(messages)
    progress_bar['value'] = 0
    progress_bar.pack(pady=10)
    
    text_console.delete(1.0, tk.END)
    for idx, message in enumerate(messages):
        username, content, timestamp = message
        formatted_message = f"[{timestamp}] <{username}> {content.strip()}"
        consoleprint(formatted_message)
        progress_bar['value'] = idx + 1
        window.update_idletasks()
    window.destroy()

# Function to ping the server
def pingserver() -> float:
    responsetime = ping(dest_addr=host)
    if responsetime is None or responsetime is False:
        consoleprint("Ping Failed")
        messagebox.showerror(title="Ping Failed", message="Host unreachable")
    else:
        consoleprint(f"Ping Success: {str(round(responsetime, 3) * 1000)}ms")
        print("ping success:", responsetime)
        messagebox.showinfo(title="Ping Sucessful", message="Response Time: " + str(round(responsetime, 3) * 1000) + "ms")

menubar = tk.Menu(root)
root.config(menu=menubar)

def showcredits():
    messagebox.showinfo(title="Credits", message="Made by GI\nWritten in Python 3.10\nSound effects from AIM and Valve")

async def disconnect(silent: bool=False):
    global websocket
    
    if websocket:
        try:
            await websocket.close(reason="Client Disconnect")
        except Exception as e:
            log(f"Error closing WebSocket: {e}")
            consoleprint(f"Error closing WebSocket: {e}")
        finally:
            websocket = None
            
        if not silent:
            playeventsound("disconnect")
        
        consoleprint("Disconnected.")
    else:
        consoleprint("Error: Not connected to a server")

async def client_exit():
    global shutdown_flag
    shutdown_flag = True  

    try:
        asyncio.create_task(disconnect())
    except Exception as e:
        consoleprint(f"Error during exit: {e}")
    
    log("Client exited")

    root.quit()
    os._exit(0)
    
async def retrieve_messages():
    data = {
        "username": username,
        "message": "RAW:MSGDB",
        "event": "request",
        "type": "msg"
        }
    await websocket.send(json.dumps(data))
    messages = await websocket.recv()
    messages = json.loads(messages)
    log(f"Retrieved {len(messages)} messages from server")
    load_messages(messages)

async def connect():
    global websocket
    global username
    uri = "ws://" + host + ":" + str(port)
    try:
        consoleprint("Connecting...")
        websocket = await websockets.connect(uri)
    except Exception as e:
        messagebox.showerror(title="Connection Error", message=e)
        consoleprint(f"Failed to connect: {e}")
    
    try:
        await websocket.send(username)
    except AttributeError:
        log("Failed to send username to server")
        consoleprint("Failed to send username to server")
    try:
        srv_info_raw = await websocket.recv()
        srv_info = json.loads(srv_info_raw)
        log(f"Connected to {uri}")
        consoleprint(f"Connected to {srv_info['name']} ({uri})\nThis server is running version {srv_info['version']}")
        data = {
            "username": username,
            "message": "RAW:USERLIST",
            "event": "request",
            "type": "msg"
            }
        await websocket.send(json.dumps(data))
        online_users = await websocket.recv()
        online_users = json.loads(online_users)
        if type(online_users) == list:
            users = ", ".join(online_users)
            consoleprint("Online Users: " + users)
        else:
            consoleprint("No one is here...")
        log(f"Retrieved user list")
        await retrieve_messages()
        playeventsound("connect")
        await receive_messages()
    except json.JSONDecodeError:
        log(f"Received invalid JSON from server: {srv_info_raw}")
        consoleprint("Failed to connect: " + srv_info_raw)
    except AttributeError:
        log(f"Failed to get server info")
        consoleprint("Failed to get server info")

async def reconnect():
    global websocket, loop
    consoleprint("Attempting to reconnect...")
    log("Reconnection attempt...")

    if websocket:
        await websocket.close()

    try:
        await connect()
    except Exception as e:
        log(f"Reconnection failed: {e}")
        consoleprint(f"Reconnection failed: {e}")

def console_clear():
    text_console.config(state=tk.NORMAL)
    text_console.delete(1.0, tk.END)
    text_console.config(state=tk.DISABLED)

def direct_connect_prompt():
    window = tk.Toplevel(root)
    window.title("Direct Connect")
    window.geometry("200x150")
    window.configure(bg="black")
    window.attributes("-topmost", True)
    window.resizable(False, False) 
    window.grab_set()
    
    label_host = tk.Label(window, text="Host (IP)", bg="black", fg="#ffffff")
    entry_host = tk.Entry(window, bg="#232323", fg="#ffffff")
    label_port = tk.Label(window, text="Port", bg="black", fg="#ffffff")
    entry_port = tk.Entry(window, bg="#232323", fg="#ffffff")
    
    def direct_connect():
        if type(str(entry_host.get())) == str:
            if type(int(entry_port.get())) == int:
                global host, port
                host = str(entry_host.get())
                port = int(entry_port.get())
                asyncio.run_coroutine_threadsafe(reconnect(), loop)
                window.destroy()
            else:
                messagebox.showerror(title="Invalid Config", message="Port must be an integer")
        else:
            messagebox.showerror(title="Invalid Config", message="Host must be a string")

    label_host.pack()
    entry_host.pack()
    label_port.pack()
    entry_port.pack()
    
    button_connect = tk.Button(window, text="Connect", width=8, bg="#232323", fg="#ffffff",
                               command=direct_connect)
    button_connect.pack(pady=16)

root.protocol("WM_DELETE_WINDOW", lambda: asyncio.run_coroutine_threadsafe(client_exit(), loop))

menu_info = tk.Menu(menubar, tearoff=0)
menu_info.add_command(label="Credits", command=showcredits)
menu_info.add_command(label="Settings", command=open_config)
menu_info.add_command(label="Exit", command=lambda: asyncio.run_coroutine_threadsafe(client_exit(), loop))
menubar.add_cascade(label="Options", menu=menu_info)

# Frame to hold buttons
frame_button = tk.Frame(root, bg="black")
frame_button.grid(row=0, column=0, padx=5, pady=5, sticky="ns")

client_icon = Image.open("assets/images/GIchat_Logo.png").resize((64, 64))
photo_icon = ImageTk.PhotoImage(client_icon)
root.iconbitmap("assets/images/GIchat_Icon.ico")
label_icon = tk.Label(frame_button, image=photo_icon, bg="black")
label_icon.pack()

button_ping = tk.Button(frame_button, text="Ping", width=8, bg="#232323", fg="#ffffff", command=pingserver)

text_console = tk.Text(root, width=90, height=10, bg="#232323", fg="#ffffff")

button_ping.pack(pady=2)

button_disconnect = tk.Button(frame_button, text="Disconnect", width=8, bg="#232323", fg="#ffffff",
                              command=lambda: asyncio.run_coroutine_threadsafe(disconnect(), loop))
button_disconnect.pack(pady=2)

button_reconnect = tk.Button(frame_button, text="Reconnect", width=8, bg="#232323", fg="#ffffff",
                             command=lambda: asyncio.run_coroutine_threadsafe(reconnect(), loop))
button_reconnect.pack(pady=2)

button_clear = tk.Button(frame_button, text="Clear", width=8, bg="#232323", fg="#ffffff", command=console_clear)
button_clear.pack(pady=2)

button_directconn = tk.Button(frame_button, text="Direct\nConnect", width=8, bg="#232323", fg="#ffffff", command=direct_connect_prompt)
button_directconn.pack(pady=2)

text_console.grid(row=0, column=1, pady=5, columnspan=2, sticky="nsew")
text_console.config(state=tk.DISABLED)

text_console.configure(font=(CLI_CONFIG["client"]["font"]["name"], CLI_CONFIG["client"]["font"]["size"]))

messagefield = tk.Text(root, bg="#232323", fg="#ffffff", height=2)
messagefield.grid(row=3, column=1, columnspan=1, pady=5, sticky="ew")

FOCUSED = True

def on_focus_in(event):
    global FOCUSED
    FOCUSED = True

def on_focus_out(event):
    global FOCUSED
    FOCUSED = False

root.bind("<FocusIn>", on_focus_in)
root.bind("<FocusOut>", on_focus_out)

async def sendmessage():
    global websocket, CLI_CONFIG
    message = messagefield.get("1.0", tk.END).strip()
    if len(message) > 2500:
        consoleprint("<server> message is too long.")
        return
    messagefield.delete("1.0", tk.END)
    if message:
        print("admin_key" in CLI_CONFIG)
        message_data = {
            "type": "msg",
            "username": username,
            "message": message,
            "event": "send_message",
            "admin_key": CLI_CONFIG["client"]["admin_key"]
            }
        
        message_json = json.dumps(message_data)
        
        if websocket and websocket.open:
            log("client sending message...")
            await websocket.send(message_json)
            log("client sent message")
            playeventsound("send_message")
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            root.after(0, consoleprint, f"[{timestamp}] <{username}> {message}")
        else:
            consoleprint("Error: Not connected to a server")

async def sendfile():
    global websocket
    file = filedialog.askopenfilename(title="Select a file", filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
    if file:
        message = b64encode(file)
        message_data = {
            "type": "file",
            "username": username,
            "data": message,
            "filename": os.path.basename(file),
            "event": "send_message"
            }
        
        message_json = json.dumps(message_data)
        
        timestamp = time.time()
        
        if websocket and websocket.open:
            log("client sending file...")
            await websocket.send(message_json)
            log(f"client sent file {os.path.basename(file)}")
            playeventsound("send_message")
            photo = Image.open(file).convert("RGB")
            photo.thumbnail((500, 500))
            photo = ImageTk.PhotoImage(photo)

            text_console.photo_ref = photo
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            consoleprint(f"[{timestamp}] <{username}> sent an image")
            text_console.image_create(tk.END, image=photo)
            consoleprint("\n")
        else:
            consoleprint("Error: Not connected to a server")

def send_click(event=None):
    asyncio.run_coroutine_threadsafe(sendmessage(), loop)
    return "break"

def insert_new_line(event=None):
    messagefield.insert(tk.INSERT, "\n")
    return "break"

messagefield.bind("<Return>", send_click)
messagefield.bind("<Shift-Return>", insert_new_line)

async def receive_messages():
    global websocket
    try:
        async for message in websocket:
            try:
                message_data = json.loads(message)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            except json.JSONDecodeError:
                consoleprint("Received invalid data: " + message)
            if message_data["event"] == "srv_message":
                if "joined" in message_data["message"]:
                    playeventsound("user_join")
                elif "left" in message_data["message"]:
                    playeventsound("user_leave")
                consoleprint(message_data["message"])
            elif message_data["event"] == "send_message":
                playeventsound("rcv_message")
                if message_data["type"] == "msg":
                    if message_data["event"] == "srv_command":
                        if message_data["message"] == "RAW:CLRMSG":
                            messages = []
                            load_messages(messages)
                    else:
                        consoleprint(f"[{timestamp}] <{message_data['username']}> {message_data['message']}")
                elif message_data["type"] == "file":
                    with open(message_data["filename"], "wb") as f:
                        f.write(b64decode(message_data["data"]))
                    photo = Image.open(message_data["filename"]).resize((256, 256))
                    photo = ImageTk.PhotoImage(photo)
                    root.after(0, consoleprint, f"[{timestamp}] <{message_data['username']}> sent an image", photo)
                    os.remove(message_data["filename"])

    except websockets.exceptions.ConnectionClosed as e:
        consoleprint(f"Connection to server closed: {e}")
        log(f"Connection to server closed: {e}")

def start_asyncio_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(connect())
    except ConnectionRefusedError:
        tk.messagebox.showerror(title="Failed to connect...", message="Error: Connection Refused")
    while not shutdown_flag:
        loop.run_forever()

button_file = tk.Button(root, width=8, text="Send\nImage", bg="#232323", fg="#ffffff",
                        command=lambda: asyncio.run_coroutine_threadsafe(sendfile(), loop))
button_file.grid(row=3, column=0)

button_send = tk.Button(root, width=5, text=">", bg="#232323", fg="#ffffff",
                        command=send_click)
button_send.grid(row=3, column=2)

asyncio_thread = threading.Thread(target=start_asyncio_loop, daemon=True)
asyncio_thread.start()

root.mainloop()