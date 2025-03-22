#!/bin/python3

import tkinter as tk
from tkinter import ttk
import requests
from io import BytesIO
from pyDes import *
import base64
import threading
from PIL import Image, ImageTk

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

######################################################################

json_data = None
player = Gst.ElementFactory.make('playbin', 'player')
is_playing = False
more_button = None

root = tk.Tk()

curr_title = tk.StringVar(value="---------")
curr_subtitle = tk.StringVar(value="---------")

curr_time = tk.DoubleVar(value=0.0)
curr_duration = tk.DoubleVar(value=100.0)

page = tk.IntVar(value=1)
max_pages = 10

curr_status = tk.StringVar(value="⏸")

######################################################################

style = ttk.Style(root)
style.layout('arrowless.Vertical.TScrollbar', 
         [('Vertical.Scrollbar.trough',
           {'children': [('Vertical.Scrollbar.thumb', 
                          {'expand': '1', 'sticky': 'nswe'})],
            'sticky': 'ns'})])

style.configure('arrowless.Vertical.TScrollbar',
                width=5,
                background='gray',
                troughcolor='black',
                gripcolor='gray',
                highlightbackground='black',
                borderwidth=0)

######################################################################

def play_song(enc, title, subtitle):
    curr_title.set(title)
    curr_subtitle.set(subtitle)
    threading.Thread(target=decrypt_url, args=(enc,)).start()
    update()


def decrypt_url(url):
    global is_playing
    global player

    player.get_bus().post(Gst.Message.new_eos())
    player.set_state(Gst.State.NULL)

    des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
    enc_url = base64.b64decode(url.strip())
    dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
    dec_url = dec_url.replace("_96.mp4", "_320.mp4")

    is_playing = True

    player.set_property('uri', dec_url)
    player.set_state(Gst.State.PLAYING)

    bus = player.get_bus()
    bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)


def update():
    curr_time.set(player.query_position(Gst.Format.TIME)[1] / Gst.SECOND)
    curr_duration.set(player.query_duration(Gst.Format.TIME)[1] / Gst.SECOND)

    start.configure(text=f"{(curr_time.get() / curr_duration.get()) * 100:.2f}%")
    slider.configure(width=(curr_time.get() / curr_duration.get() * 800))

    root.after(1000, update)

######################################################################

def toggle_play(event):
    global player
    global is_playing

    if not isinstance(event.widget, tk.Entry):
        if is_playing:
            player.set_state(Gst.State.PAUSED)
            curr_status.set("▶︎")
        else:
            player.set_state(Gst.State.PLAYING)
            curr_status.set("⏸")
        
        is_playing = not is_playing

######################################################################

def on_app_close():
    global player

    player.get_bus().post(Gst.Message.new_eos())
    player.set_state(Gst.State.NULL)
    player = None
    root.destroy()

######################################################################

def search(event=None, p=1):
    global json_data

    if p == 1:
        for widget in results_frame.winfo_children():
            widget.destroy()

    scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(10, 125))
    
    url = f"https://www.jiosaavn.com/api.php?_format=json&_marker=0&api_version=4&ctx=web6dot0&__call=search.getResults&q={input.get()}&p={p}"
    
    response = requests.get(url)
    
    json_data = response.json()
    
    threading.Thread(target=add_search_items, args=(json_data,)).start()


def add_search_items(json_data):
    global more_button

    if more_button != None:
        more_button.destroy()
        more_button = None

    for song in json_data['results']:
        title = song['title']
        subtitle = song['subtitle']
        img_url = song['image'].replace('150x150', '50x50')
        enc = song['more_info']['encrypted_media_url']

        song_container = tk.Frame(results_frame, bg="black", width=850, height=50)
        song_container.pack_propagate(False)

        img_response = requests.get(img_url)
        img_data = img_response.content
        img = Image.open(BytesIO(img_data))
        photo = ImageTk.PhotoImage(img)

        song_img = tk.Label(song_container, image=photo, bg="black")
        song_img.configure(height=50, width=50)
        song_img.pack(side=tk.LEFT, padx=(0, 5))
        song_img.image = photo

        song_details = tk.Frame(song_container, bg="black")

        song_title = tk.Label(song_details, text=title, bg="black", fg="white",
                              font=('GitLab Sans', 12), justify="left")

        song_subtitle = tk.Label(song_details, text=subtitle[:70] + "...",
                                 bg="black", fg="gray", font=('GitLab Sans', 10), justify="left")

        song_title.pack(anchor="w")
        song_subtitle.pack(anchor="w")
        song_details.pack(side=tk.LEFT)

        highlight = tk.Frame(song_container, bg="black", width=5)
        highlight.pack(fill=tk.Y, side="right")

        song_container.pack(pady=(0, 10))

        song_container.bind("<Button-1>", lambda event, enc=enc, title=title, subtitle=subtitle: play_song(enc, title, subtitle))
        song_title.bind("<Button-1>", lambda event, enc=enc, title=title, subtitle=subtitle: play_song(enc, title, subtitle))
        song_subtitle.bind("<Button-1>", lambda event, enc=enc, title=title, subtitle=subtitle: play_song(enc, title, subtitle))
        song_img.bind("<Button-1>", lambda event, enc=enc, title=title, subtitle=subtitle: play_song(enc, title, subtitle))

        song_container.bind("<Enter>", lambda event, cont=highlight: cont.config(bg='red'))
        song_container.bind("<Leave>", lambda event, cont=highlight: cont.config(bg='black'))

        hr = tk.Frame(results_frame, bg="#292929", height=1)
        hr.pack(fill=tk.X, pady=(0, 10))

    page.set(page.get() + 1)

    def more_func():
        if not page.get() > max_pages:
            search(p=page.get())

    if more_button == None and not page.get() > max_pages:
        more_button = tk.Button(results_frame, text="More", bg="#292929", fg="white", bd=1,
                     highlightbackground='#484848', highlightcolor="gray", justify="center",
                                font=('GitLab Sans', 14), relief='flat', takefocus=0,
                                command=more_func)
        more_button.pack(side="bottom", fill="x", expand=True)


######################################################################

root.configure(bg='#030303')
root.title("Halo")

def select_all(event):
    input.select_range(0, tk.END)
    input.icursor(tk.END)
    return "break"

input = tk.Entry(root, width=40, bg="#292929", fg="white", bd=1,
                 highlightbackground='#484848', highlightcolor="gray", justify="center",
                 font=('GitLab Sans', 14), relief='flat', insertbackground='white',
                 selectbackground="blue", selectforeground="white", takefocus=0)
input.pack(pady=20)
input.bind("<Control-a>", select_all)
input.bind('<Return>', lambda p=1: search(page.get()))

canvas = tk.Canvas(root,bg="black", width=850, borderwidth=0, highlightthickness=0)

scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview, style='arrowless.Vertical.TScrollbar')

results_frame = tk.Frame(canvas, bg="black", width=850)
results_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

canvas.create_window((0, 0), window=results_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

canvas.pack(side="left", fill="y", expand=True, pady=(10, 125))

######################################################################

miniplayer = tk.Frame(root, bg="black", highlightbackground="#292929",
                   highlightcolor="#292929", highlightthickness=1, relief="groove")
miniplayer.place(relx=0.5, rely=1.0, anchor='s', width=800, y=-10)

######################################################################

slider = tk.Frame(miniplayer, bg="red", height=6)
slider.pack(side="top", anchor="w")

def on_click(event): update_seekbar(event.x)
def on_drag(event): update_seekbar(event.x)

slider.bind("<Button-1>", on_click)
slider.bind("<B1-Motion>", on_drag)

def update_seekbar(x):
    new_width = max(0, min(x, 800))
    slider.configure(width=new_width)

    newtime = ((new_width / 800) * curr_duration.get()) * Gst.SECOND
    player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, newtime)

######################################################################

duration_box = tk.Frame(miniplayer, bg="black")
duration_box.pack(fill="both", expand=True)

start = tk.Label(duration_box, font=("GitLab Sans", 8), bg="black", fg="white")
start.pack(side="left", padx=(5, 0))

end = tk.Label(duration_box, textvariable=curr_duration,
               font=("GitLab Sans", 8), bg="black", fg="white")
end.pack(side="right", padx=(0, 5))

######################################################################

song_details_box = tk.Frame(miniplayer, bg="black")
song_details_box.pack(fill="both", expand=True)

title_label = tk.Label(song_details_box, textvariable=curr_title,
                       font=("GitLab Sans", 10), bg="black", fg="white")
title_label.pack(side="left", padx=(5, 0))

subtitle_label = tk.Label(song_details_box, textvariable=curr_subtitle,
                          font=("GitLab Sans", 10), bg="black", fg="white")
subtitle_label.pack(side="right", padx=(0, 5))

######################################################################

play_button = tk.Label(miniplayer, textvariable=curr_status,
                       bg="black", fg="white", font=("monospace", 22))
play_button.pack(side=tk.BOTTOM)
play_button.bind("<Button-1>", lambda event: toggle_play(event))
root.bind("<space>", toggle_play)

root.protocol("WM_DELETE_WINDOW", on_app_close)
root.mainloop()
