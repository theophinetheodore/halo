import tkinter as tk
from tkinter import ttk
import requests
from io import BytesIO
from pyDes import *
import base64
import threading
from PIL import Image, ImageTk

######################################################################

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

######################################################################

json_data = None
player = Gst.ElementFactory.make('playbin', 'player')
is_playing = False

root = tk.Tk()

style = ttk.Style()
style.theme_use('alt')
style.configure("TScale", 
                troughcolor="#292929",
                background="black",
                sliderrelief="flat",
                lightcolor="white",
                sliderlength=30)

curr_title = tk.StringVar(value="---------")
curr_subtitle = tk.StringVar(value="---------")

curr_time = tk.DoubleVar(value=0.0)
curr_duration = tk.DoubleVar(value=100.0)

curr_status = tk.StringVar(value="▶︎")

scale = None

######################################################################

def decrypt_url(url):
    global is_playing
    global player

    player.set_state(Gst.State.NULL)

    des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
    enc_url = base64.b64decode(url.strip())
    dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
    dec_url = dec_url.replace("_96.mp4", "_320.mp4")

    player.set_property('uri', dec_url)
    player.set_state(Gst.State.PLAYING)
    is_playing = True

    bus = player.get_bus()
    bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)

######################################################################

def play_song(enc, title, subtitle):
    curr_title.set(title)
    curr_subtitle.set(subtitle)
    threading.Thread(target=decrypt_url, args=(enc,)).start()
    continuously_update_time()

def continuously_update_time():
    global scale

    curr_time.set(player.query_position(Gst.Format.TIME)[1] / Gst.SECOND)
    curr_duration.set(player.query_duration(Gst.Format.TIME)[1] / Gst.SECOND)
    scale.configure(to = curr_duration.get())
    start.configure(text=f"{(curr_time.get() / curr_duration.get()) * 100:.2f}%")
    root.after(1000, continuously_update_time)

######################################################################

def toggle_play():
    global player
    global is_playing

    if is_playing:
        player.set_state(Gst.State.PAUSED)
        curr_status.set("▶︎")
    else:
        player.set_state(Gst.State.PLAYING)
        curr_status.set("⏸")
    
    is_playing = not is_playing

######################################################################

def search(event=None):
    global json_data

    for widget in results_frame.winfo_children():
        widget.destroy()
    
    user_input = input.get()
    
    url = f"https://www.jiosaavn.com/api.php?_format=json&_marker=0&api_version=4&ctx=web6dot0&__call=search.getResults&q={user_input}&n=15"
    
    response = requests.get(url)
    
    json_data = response.json()
    
    for song in json_data['results']:
        title = song['title']
        subtitle = song['subtitle']
        img_url = song['image'].replace('150x150', '50x50')
        enc = song['more_info']['encrypted_media_url']

        song_container = tk.Frame(results_frame, bg="black", width=800, height=50)
        song_container.pack_propagate(False)

        img_response = requests.get(img_url)
        img_data = img_response.content
        img = Image.open(BytesIO(img_data))
        # img = img.resize((50, 50), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        song_img = tk.Label(song_container, image=photo, bg="black")
        song_img.configure(height=50, width=50)
        song_img.pack(side=tk.LEFT, padx=(0, 5))
        song_img.image = photo

        song_details = tk.Frame(song_container, bg="black")

        song_title = tk.Label(song_details, text=title, bg="black", fg="white",
                              font=('GitLab Sans', 12), justify="left")
        song_subtitle = tk.Label(song_details, text=subtitle[:70] + "...", bg="black", fg="gray", font=('GitLab Sans', 10), justify="left")

        song_title.pack(anchor="w")
        song_subtitle.pack(anchor="w")
        song_details.pack(side=tk.LEFT)

        highlight = tk.Frame(song_container, bg="black", width=10)
        highlight.pack(fill=tk.Y, side="right")

        song_container.pack(pady=(0, 10))
        song_container.bind("<Button-1>", lambda event, enc=enc, title=title, subtitle=subtitle: play_song(enc, title, subtitle))
        song_container.bind("<Enter>", lambda event, cont=highlight: cont.config(bg='dodgerblue'))
        song_container.bind("<Leave>", lambda event, cont=highlight: cont.config(bg='black'))

        hr = tk.Frame(results_frame, bg="#292929", height=1)
        hr.pack(fill=tk.X, pady=(0, 10))

    scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(10, 135))

######################################################################

root.configure(bg='#030303')
root.title("music")

input = tk.Entry(root, width=40, bg="#292929", bd=1, highlightbackground='#484848', highlightcolor="gray", justify="center",
                 fg="white", font=('GitLab Sans', 14), relief='flat', insertbackground='white')
input.pack(pady=20)
input.bind('<Return>', search)

canvas = tk.Canvas(root,bg="black", width=850, borderwidth=0, highlightthickness=0)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.config(width=10, bg='#484848', activebackground='#484848', highlightbackground='black', troughcolor="black", bd=0)

results_frame = tk.Frame(canvas, bg="black", width=850)
results_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

canvas.create_window((0, 0), window=results_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

canvas.pack(side="left", fill="y", expand=True, pady=(10, 135))

######################################################################

playbox = tk.Frame(root, bg="black", highlightbackground="#292929",
                   highlightcolor="#292929", highlightthickness=1, relief="groove")
playbox.place(relx=0.5, rely=1.0, anchor='s', width=800, y=-20)

durbox = tk.Frame(playbox, bg="black")
durbox.pack(fill="both", expand=True)

start = tk.Label(durbox, text="0.0%", font=("GitLab Sans", 8), bg="black", fg="white")
start.pack(side="left", padx=(5, 0))

scale = ttk.Scale(durbox, variable=curr_time, from_=curr_time.get(), to=curr_duration.get(), orient=tk.HORIZONTAL)
scale.pack(side="left", fill=tk.X, expand=True)

def on_scale_change(event):
    position_ns = curr_time.get() * Gst.SECOND
    success = player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, position_ns)

scale.bind("<ButtonRelease-1>", on_scale_change)

end = tk.Label(durbox, textvariable=curr_duration, font=("GitLab Sans", 8), bg="black", fg="white")
end.pack(side="right", padx=(0, 5))

######################################################################

title_label = tk.Label(playbox, textvariable=curr_title,
                       font=("GitLab Sans", 12), bg="black", fg="white")
title_label.pack()

subtitle_label = tk.Label(playbox, textvariable=curr_subtitle,
                          font=("GitLab Sans", 10), bg="black", fg="white")
subtitle_label.pack()

play_button = tk.Label(playbox, textvariable=curr_status, bg="black", fg="white", font=("monospace", 22))
play_button.pack(side=tk.BOTTOM, pady=10)
play_button.bind("<Button-1>", lambda event: toggle_play())

root.mainloop()
