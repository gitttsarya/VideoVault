"""
VideoVault — Social Media Video Downloader
Auto-downloads yt-dlp + ffmpeg on first run. No bat file needed.
"""
import customtkinter as ctk
import threading
import subprocess
import os, sys, re, json, shutil, urllib.request, zipfile
from pathlib import Path
from tkinter import filedialog, messagebox

APP_NAME    = "VideoVault"
APP_VERSION = "1.0.0"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

TOOLS_DIR   = BASE_DIR / "tools"
YTDLP_EXE  = TOOLS_DIR / "yt-dlp.exe"
FFMPEG_EXE = TOOLS_DIR / "ffmpeg.exe"
CONFIG_FILE = BASE_DIR / "videovault.json"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)

YTDLP_URL  = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT="#6C63FF"; ACCENT_DARK="#4F46E5"; BG_DARK="#0A0A0F"; BG_CARD="#13131A"
BG_SURFACE="#1C1C25"; BG_HOVER="#252530"; TEXT_PRIMARY="#F0EEFF"; TEXT_MUTED="#6B6B80"
TEXT_DIM="#3A3A50"; SUCCESS="#22C55E"; ERROR="#EF4444"; WARNING="#F59E0B"; BORDER="#2A2A38"

PLATFORMS={"YouTube":"▶","TikTok":"♪","Instagram":"◈","Twitter/X":"✦","Facebook":"⬡","Reddit":"◉","Twitch":"▣","Vimeo":"◎","Other":"◆"}
QUALITY_OPTIONS=["Best Available","4K (2160p)","1080p (Full HD)","720p (HD)","480p (SD)","360p","Audio Only (MP3)","Audio Only (M4A)"]
FORMAT_MAP={"Best Available":"bestvideo+bestaudio/best","4K (2160p)":"bestvideo[height<=2160]+bestaudio/best[height<=2160]","1080p (Full HD)":"bestvideo[height<=1080]+bestaudio/best[height<=1080]","720p (HD)":"bestvideo[height<=720]+bestaudio/best[height<=720]","480p (SD)":"bestvideo[height<=480]+bestaudio/best[height<=480]","360p":"bestvideo[height<=360]+bestaudio/best[height<=360]","Audio Only (MP3)":"bestaudio/best","Audio Only (M4A)":"bestaudio/best"}

def load_config():
    d={"output_dir":str(Path.home()/"Downloads"/"VideoVault"),"default_quality":"Best Available","theme":"dark","setup_done":False}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f: d.update(json.load(f))
        except: pass
    return d

def save_config(c):
    try:
        with open(CONFIG_FILE,"w") as f: json.dump(c,f,indent=2)
    except: pass

def detect_platform(url):
    u=url.lower()
    if "youtube.com" in u or "youtu.be" in u: return "YouTube"
    if "tiktok.com" in u: return "TikTok"
    if "instagram.com" in u: return "Instagram"
    if "twitter.com" in u or "x.com" in u: return "Twitter/X"
    if "facebook.com" in u or "fb.watch" in u: return "Facebook"
    if "reddit.com" in u or "v.redd.it" in u: return "Reddit"
    if "twitch.tv" in u: return "Twitch"
    if "vimeo.com" in u: return "Vimeo"
    return "Other"

def tools_ready(): return YTDLP_EXE.exists() and FFMPEG_EXE.exists()


class SetupWizard(ctk.CTkToplevel):
    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete=on_complete
        self.title("VideoVault — First Time Setup")
        self.geometry("500x400")
        self.resizable(False,False)
        self.configure(fg_color=BG_DARK)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda:None)
        self._build()

    def _build(self):
        ctk.CTkLabel(self,text="⬇",font=("Segoe UI",52),text_color=ACCENT).pack(pady=(28,0))
        ctk.CTkLabel(self,text="VideoVault",font=("Segoe UI",22,"bold"),text_color=TEXT_PRIMARY).pack()
        ctk.CTkLabel(self,text="One-time setup: downloading yt-dlp + ffmpeg",font=("Segoe UI",11),text_color=TEXT_MUTED).pack(pady=(4,20))
        card=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=12); card.pack(fill="x",padx=32)
        self.step_lbl=ctk.CTkLabel(card,text="Starting…",font=("Segoe UI",12,"bold"),text_color=TEXT_PRIMARY); self.step_lbl.pack(pady=(20,4))
        self.detail_lbl=ctk.CTkLabel(card,text="",font=("Segoe UI",10),text_color=TEXT_MUTED); self.detail_lbl.pack()
        self.bar=ctk.CTkProgressBar(card,height=8,corner_radius=4,fg_color=BG_SURFACE,progress_color=ACCENT); self.bar.set(0); self.bar.pack(fill="x",padx=20,pady=(14,8))
        self.pct_lbl=ctk.CTkLabel(card,text="0%",font=("Segoe UI",10),text_color=TEXT_MUTED); self.pct_lbl.pack(pady=(0,20))
        ctk.CTkLabel(self,text="This happens only once. The app will open when ready.",font=("Segoe UI",10),text_color=TEXT_DIM).pack(pady=16)
        threading.Thread(target=self._run,daemon=True).start()

    def _set(self,step,detail,pct):
        def _do():
            self.step_lbl.configure(text=step)
            self.detail_lbl.configure(text=detail)
            self.bar.set(pct/100)
            self.pct_lbl.configure(text=f"{pct}%")
        self.after(0,_do)

    def _run(self):
        try:
            if not YTDLP_EXE.exists():
                self._set("Downloading yt-dlp…","(~12 MB)",5)
                self._dl(YTDLP_URL,YTDLP_EXE,5,45)
            else:
                self._set("yt-dlp ready","",45)
            if not FFMPEG_EXE.exists():
                self._set("Downloading ffmpeg…","(~70 MB — please wait)",46)
                tmp=TOOLS_DIR/"ffmpeg.zip"
                self._dl(FFMPEG_URL,tmp,46,88)
                self._set("Extracting ffmpeg…","",89)
                self._extract(tmp); tmp.unlink(missing_ok=True)
            else:
                self._set("ffmpeg ready","",88)
            self._set("All done!","",100)
            self.after(800,self._finish)
        except Exception as e:
            self.after(0,lambda:self.step_lbl.configure(text=f"Error: {e}",text_color=ERROR))

    def _dl(self,url,dest,s,e):
        step_text=self.step_lbl.cget("text")
        def hook(b,bs,tot):
            if tot>0:
                pct=int(s+(min(b*bs/tot,1.0))*(e-s))
                mb=b*bs/1048576; mbt=tot/1048576
                self._set(step_text,f"{mb:.1f} / {mbt:.1f} MB",pct)
        urllib.request.urlretrieve(url,dest,hook)

    def _extract(self,zp):
        with zipfile.ZipFile(zp) as z:
            m=[x for x in z.namelist() if x.endswith("ffmpeg.exe")]
            if not m: raise RuntimeError("ffmpeg.exe not in zip")
            with z.open(m[0]) as src, open(FFMPEG_EXE,"wb") as dst:
                shutil.copyfileobj(src,dst)

    def _finish(self): self.destroy(); self.on_complete()


class DownloadCard(ctk.CTkFrame):
    def __init__(self,master,url,quality,output_dir,on_done,**kw):
        super().__init__(master,fg_color=BG_SURFACE,corner_radius=10,border_width=1,border_color=BORDER,**kw)
        self.url=url; self.quality=quality; self.output_dir=output_dir; self.on_done=on_done
        self.process=None; self._cancelled=False
        p=detect_platform(url); sym=PLATFORMS.get(p,"◆")
        self.columnconfigure(1,weight=1)
        ctk.CTkLabel(self,text=sym,font=("Segoe UI",20,"bold"),fg_color=BG_CARD,corner_radius=8,width=44,height=44,text_color=ACCENT).grid(row=0,column=0,rowspan=3,padx=(12,10),pady=12,sticky="n")
        ctk.CTkLabel(self,text=f"{p}  ·  {quality}",font=("Segoe UI",11,"bold"),text_color=TEXT_PRIMARY).grid(row=0,column=1,sticky="w",pady=(12,0))
        short=url if len(url)<66 else url[:63]+"…"
        ctk.CTkLabel(self,text=short,font=("Segoe UI",10),text_color=TEXT_MUTED).grid(row=1,column=1,sticky="w")
        self.bar=ctk.CTkProgressBar(self,height=5,corner_radius=3,fg_color=BG_CARD,progress_color=ACCENT); self.bar.set(0)
        self.bar.grid(row=2,column=1,sticky="ew",padx=(0,12),pady=(6,2))
        self.status_lbl=ctk.CTkLabel(self,text="Queued",font=("Segoe UI",10),text_color=TEXT_MUTED); self.status_lbl.grid(row=3,column=1,sticky="w",pady=(0,10))
        self.cancel_btn=ctk.CTkButton(self,text="✕",width=26,height=26,fg_color="transparent",hover_color=BG_HOVER,text_color=TEXT_MUTED,font=("Segoe UI",11),command=self.cancel)
        self.cancel_btn.grid(row=0,column=2,padx=(0,10),pady=(12,0),sticky="ne")

    def start(self): threading.Thread(target=self._download,daemon=True).start()

    def cancel(self):
        self._cancelled=True
        if self.process:
            try: self.process.terminate()
            except: pass
        self.after(0,lambda:(self.status_lbl.configure(text="Cancelled",text_color=ERROR),self.bar.configure(progress_color=ERROR),self.cancel_btn.configure(state="disabled")))
        self.on_done(False)

    def _st(self,msg,color=None):
        c=color or TEXT_MUTED
        self.after(0,lambda:self.status_lbl.configure(text=msg,text_color=c))

    def _download(self):
        self._st("Fetching info…")
        fmt=FORMAT_MAP.get(self.quality,"bestvideo+bestaudio/best")
        is_audio="Audio Only" in self.quality
        ext_flag=["--extract-audio","--audio-format","mp3" if "MP3" in self.quality else "m4a"] if is_audio else []
        cmd=[str(YTDLP_EXE),"--newline","--no-warnings","--ffmpeg-location",str(FFMPEG_EXE.parent),"-f",fmt,*ext_flag,"--merge-output-format","mp4" if not is_audio else ("mp3" if "MP3" in self.quality else "m4a"),"-o",os.path.join(self.output_dir,"%(title)s.%(ext)s"),self.url]
        try:
            flags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
            self.process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,creationflags=flags)
            for line in self.process.stdout:
                if self._cancelled: break
                self._parse(line.strip())
            self.process.wait()
            if self._cancelled: return
            if self.process.returncode==0: self.after(0,self._success)
            else: self._st("Download failed",ERROR); self.after(0,lambda:self.bar.configure(progress_color=ERROR)); self.on_done(False)
        except FileNotFoundError: self._st("yt-dlp not found",ERROR); self.on_done(False)
        except Exception as e: self._st(str(e)[:80],ERROR); self.on_done(False)

    def _parse(self,line):
        m=re.search(r"\[download\]\s+([\d.]+)%",line)
        if m:
            pct=float(m.group(1))/100
            sp=re.search(r"at\s+([\d.]+\S+)",line); eta=re.search(r"ETA\s+(\S+)",line)
            txt=f"Downloading  {int(pct*100)}%"
            if sp: txt+=f"  ·  {sp.group(1)}"
            if eta: txt+=f"  ·  ETA {eta.group(1)}"
            self.after(0,lambda p=pct,t=txt:(self.bar.set(p),self.status_lbl.configure(text=t,text_color=TEXT_PRIMARY)))
        elif "[Merger]" in line or "[ffmpeg]" in line: self._st("Processing with ffmpeg…",WARNING)
        elif "[ExtractAudio]" in line: self._st("Extracting audio…",WARNING)

    def _success(self):
        self.bar.set(1); self.bar.configure(progress_color=SUCCESS)
        self.status_lbl.configure(text="Complete!",text_color=SUCCESS)
        self.cancel_btn.configure(state="disabled"); self.on_done(True)


class SettingsPanel(ctk.CTkFrame):
    def __init__(self,master,cfg,on_save,**kw):
        super().__init__(master,fg_color="transparent",**kw)
        self.cfg=cfg; self.on_save=on_save; self._build()

    def _build(self):
        self.columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text="Settings",font=("Segoe UI",18,"bold"),text_color=TEXT_PRIMARY).grid(row=0,column=0,sticky="w",pady=(0,20))
        # Output folder
        ctk.CTkLabel(self,text="OUTPUT FOLDER",font=("Segoe UI",9,"bold"),text_color=TEXT_MUTED).grid(row=1,column=0,sticky="w")
        row=ctk.CTkFrame(self,fg_color="transparent"); row.grid(row=2,column=0,sticky="ew",pady=(4,16)); row.columnconfigure(0,weight=1)
        self.folder_var=ctk.StringVar(value=self.cfg.get("output_dir",""))
        ctk.CTkEntry(row,textvariable=self.folder_var,fg_color=BG_SURFACE,border_color=BORDER,text_color=TEXT_PRIMARY,font=("Segoe UI",11),height=38).grid(row=0,column=0,sticky="ew",padx=(0,8))
        ctk.CTkButton(row,text="Browse",width=80,height=38,fg_color=BG_SURFACE,hover_color=BG_HOVER,text_color=TEXT_MUTED,corner_radius=8,command=self._browse).grid(row=0,column=1)
        # Quality
        ctk.CTkLabel(self,text="DEFAULT QUALITY",font=("Segoe UI",9,"bold"),text_color=TEXT_MUTED).grid(row=3,column=0,sticky="w")
        self.quality_var=ctk.StringVar(value=self.cfg.get("default_quality","Best Available"))
        ctk.CTkOptionMenu(self,values=QUALITY_OPTIONS,variable=self.quality_var,font=("Segoe UI",12),fg_color=BG_SURFACE,button_color=ACCENT_DARK,button_hover_color=ACCENT,dropdown_fg_color=BG_CARD,text_color=TEXT_PRIMARY,height=38,corner_radius=8,dynamic_resizing=False).grid(row=4,column=0,sticky="w",pady=(4,16))
        # Theme
        ctk.CTkLabel(self,text="THEME",font=("Segoe UI",9,"bold"),text_color=TEXT_MUTED).grid(row=5,column=0,sticky="w")
        self.theme_var=ctk.StringVar(value=self.cfg.get("theme","dark").title())
        ctk.CTkSegmentedButton(self,values=["Dark","Light","System"],variable=self.theme_var,font=("Segoe UI",11),fg_color=BG_SURFACE,selected_color=ACCENT,selected_hover_color=ACCENT_DARK,unselected_color=BG_SURFACE,text_color=TEXT_PRIMARY,height=36).grid(row=6,column=0,sticky="w",pady=(4,16))
        # Re-setup
        ctk.CTkLabel(self,text="TOOLS",font=("Segoe UI",9,"bold"),text_color=TEXT_MUTED).grid(row=7,column=0,sticky="w")
        ctk.CTkButton(self,text="Re-download yt-dlp + ffmpeg",font=("Segoe UI",11),fg_color=BG_SURFACE,hover_color=BG_HOVER,text_color=TEXT_MUTED,height=38,border_width=1,border_color=BORDER,corner_radius=8,command=self._rerun).grid(row=8,column=0,sticky="w",pady=(4,20))
        ctk.CTkButton(self,text="Save Settings",font=("Segoe UI",13,"bold"),fg_color=ACCENT,hover_color=ACCENT_DARK,text_color="white",height=42,corner_radius=8,command=self._save).grid(row=9,column=0,sticky="w")

    def _browse(self):
        d=filedialog.askdirectory(initialdir=self.folder_var.get())
        if d: self.folder_var.set(d)

    def _rerun(self):
        if messagebox.askyesno("Re-run Setup","Delete and re-download yt-dlp and ffmpeg?"):
            YTDLP_EXE.unlink(missing_ok=True); FFMPEG_EXE.unlink(missing_ok=True)
            # walk up to app
            w=self
            while w and not isinstance(w,VideoVaultApp): w=w.master
            if w: w._run_setup()

    def _save(self):
        self.cfg["output_dir"]=self.folder_var.get()
        self.cfg["default_quality"]=self.quality_var.get()
        self.cfg["theme"]=self.theme_var.get().lower()
        save_config(self.cfg); ctk.set_appearance_mode(self.cfg["theme"])
        self.on_save(self.cfg)
        messagebox.showinfo("Saved","Settings saved!")


class AboutPanel(ctk.CTkFrame):
    def __init__(self,master,**kw):
        super().__init__(master,fg_color="transparent",**kw)
        self.columnconfigure(0,weight=1)
        card=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=16); card.grid(row=0,column=0,sticky="nsew"); card.columnconfigure(0,weight=1)
        ctk.CTkLabel(card,text="⬇",font=("Segoe UI",56),text_color=ACCENT).grid(row=0,pady=(36,0))
        ctk.CTkLabel(card,text="VideoVault",font=("Segoe UI",28,"bold"),text_color=TEXT_PRIMARY).grid(row=1)
        ctk.CTkLabel(card,text=f"Version {APP_VERSION}",font=("Segoe UI",12),text_color=TEXT_MUTED).grid(row=2,pady=(2,24))
        for label,val in [("Backend","yt-dlp + ffmpeg (auto-bundled)"),("UI","Python + CustomTkinter"),("Supports","YouTube, TikTok, Instagram, Twitter/X,\nFacebook, Reddit, Twitch, Vimeo + 1000s more"),("Output","~/Downloads/VideoVault  (configurable)")]:
            r=ctk.CTkFrame(card,fg_color=BG_SURFACE,corner_radius=8); r.grid(sticky="ew",padx=32,pady=3); r.columnconfigure(1,weight=1)
            ctk.CTkLabel(r,text=label,font=("Segoe UI",11,"bold"),text_color=TEXT_MUTED,width=90,anchor="w").grid(row=0,column=0,padx=(14,8),pady=10)
            ctk.CTkLabel(r,text=val,font=("Segoe UI",11),text_color=TEXT_PRIMARY,anchor="w",justify="left").grid(row=0,column=1,sticky="w",padx=(0,14))
        ctk.CTkLabel(card,text="Made with open-source tools ❤",font=("Segoe UI",10),text_color=TEXT_DIM).grid(row=99,pady=(20,32))


class VideoVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg=load_config()
        os.makedirs(self.cfg["output_dir"],exist_ok=True)
        self.title("VideoVault"); self.geometry("900x680"); self.minsize(740,560); self.configure(fg_color=BG_DARK)
        self._dl_total=0; self._dl_done=0
        self._build_ui()
        if not tools_ready(): self.after(300,self._run_setup)

    def _build_ui(self):
        self.columnconfigure(1,weight=1); self.rowconfigure(0,weight=1)
        self._build_sidebar(); self._build_content()

    def _build_sidebar(self):
        side=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=0,width=196); side.grid(row=0,column=0,sticky="nsew"); side.grid_propagate(False); side.columnconfigure(0,weight=1)
        ctk.CTkLabel(side,text="⬇",font=("Segoe UI",30,"bold"),text_color=ACCENT).grid(row=0,pady=(26,0))
        ctk.CTkLabel(side,text="VideoVault",font=("Segoe UI",14,"bold"),text_color=TEXT_PRIMARY).grid(row=1,pady=(4,24))
        self._nav_btns={}
        for i,(label,icon,cmd) in enumerate([("Download","⬇",self._show_downloader),("Settings","⚙",self._show_settings),("About","◈",self._show_about)]):
            btn=ctk.CTkButton(side,text=f"  {icon}  {label}",font=("Segoe UI",12),fg_color="transparent",hover_color=BG_SURFACE,text_color=TEXT_MUTED,anchor="w",height=40,corner_radius=8,command=cmd)
            btn.grid(row=i+2,sticky="ew",padx=10,pady=2); self._nav_btns[label]=btn
        ctk.CTkLabel(side,text=f"v{APP_VERSION}",font=("Segoe UI",9),text_color=TEXT_DIM).grid(row=99,pady=14,sticky="s"); side.rowconfigure(98,weight=1)
        self._set_nav("Download")

    def _set_nav(self,active):
        for l,b in self._nav_btns.items():
            b.configure(fg_color=BG_SURFACE if l==active else "transparent",text_color=ACCENT if l==active else TEXT_MUTED)

    def _build_content(self):
        self.content=ctk.CTkFrame(self,fg_color="transparent"); self.content.grid(row=0,column=1,sticky="nsew",padx=20,pady=20); self.content.columnconfigure(0,weight=1); self.content.rowconfigure(0,weight=1)
        self._show_downloader()

    def _clear_content(self):
        for w in self.content.winfo_children(): w.destroy()

    def _show_downloader(self): self._clear_content(); self._set_nav("Download"); self._build_downloader(self.content)
    def _show_settings(self): self._clear_content(); self._set_nav("Settings"); SettingsPanel(self.content,self.cfg,self._on_settings_save).grid(row=0,column=0,sticky="nsew")
    def _show_about(self): self._clear_content(); self._set_nav("About"); AboutPanel(self.content).grid(row=0,column=0,sticky="nsew")
    def _on_settings_save(self,cfg): self.cfg=cfg; os.makedirs(cfg["output_dir"],exist_ok=True)

    def _build_downloader(self,parent):
        parent.rowconfigure(2,weight=1)
        card=ctk.CTkFrame(parent,fg_color=BG_CARD,corner_radius=14,border_width=1,border_color=BORDER); card.grid(row=0,column=0,sticky="ew",pady=(0,14)); card.columnconfigure(0,weight=1)
        ctk.CTkLabel(card,text="VIDEO URL",font=("Segoe UI",9,"bold"),text_color=TEXT_MUTED).grid(row=0,column=0,columnspan=3,sticky="w",padx=16,pady=(16,4))
        self.url_var=ctk.StringVar()
        self.url_entry=ctk.CTkEntry(card,textvariable=self.url_var,placeholder_text="Paste a YouTube, TikTok, Instagram, Twitter/X, Facebook, Reddit… URL",font=("Segoe UI",12),height=42,fg_color=BG_SURFACE,border_color=BORDER,border_width=1,corner_radius=8,text_color=TEXT_PRIMARY)
        self.url_entry.grid(row=1,column=0,sticky="ew",padx=(16,8)); self.url_entry.bind("<Return>",lambda e:self._add_download())
        ctk.CTkButton(card,text="Paste",width=72,height=42,fg_color=BG_SURFACE,hover_color=BG_HOVER,text_color=TEXT_MUTED,corner_radius=8,command=self._paste_url).grid(row=1,column=1,padx=(0,16))
        ctk.CTkLabel(card,text="QUALITY",font=("Segoe UI",9,"bold"),text_color=TEXT_MUTED).grid(row=2,column=0,sticky="w",padx=16,pady=(12,4))
        qrow=ctk.CTkFrame(card,fg_color="transparent"); qrow.grid(row=3,column=0,columnspan=2,sticky="ew",padx=16,pady=(0,14)); qrow.columnconfigure(0,weight=1)
        self.quality_var=ctk.StringVar(value=self.cfg.get("default_quality","Best Available"))
        ctk.CTkOptionMenu(qrow,values=QUALITY_OPTIONS,variable=self.quality_var,font=("Segoe UI",12),fg_color=BG_SURFACE,button_color=ACCENT_DARK,button_hover_color=ACCENT,dropdown_fg_color=BG_CARD,text_color=TEXT_PRIMARY,height=42,corner_radius=8,dynamic_resizing=False).grid(row=0,column=0,sticky="ew",padx=(0,10))
        ctk.CTkButton(qrow,text="⬇  Download",font=("Segoe UI",13,"bold"),fg_color=ACCENT,hover_color=ACCENT_DARK,text_color="white",height=42,corner_radius=8,width=158,command=self._add_download).grid(row=0,column=1)
        ctk.CTkLabel(card,text="── Batch: paste multiple URLs, one per line ──",font=("Segoe UI",9),text_color=TEXT_DIM).grid(row=4,column=0,columnspan=3,pady=(0,5))
        brow=ctk.CTkFrame(card,fg_color="transparent"); brow.grid(row=5,column=0,columnspan=3,sticky="ew",padx=16,pady=(0,14)); brow.columnconfigure(0,weight=1)
        self.batch_txt=ctk.CTkTextbox(brow,height=62,font=("Segoe UI",11),fg_color=BG_SURFACE,border_color=BORDER,border_width=1,corner_radius=8,text_color=TEXT_PRIMARY); self.batch_txt.grid(row=0,column=0,sticky="ew",padx=(0,8))
        ctk.CTkButton(brow,text="Add All",width=80,height=62,fg_color=ACCENT_DARK,hover_color=ACCENT,text_color="white",corner_radius=8,command=self._add_batch).grid(row=0,column=1)
        chips=ctk.CTkFrame(card,fg_color="transparent"); chips.grid(row=6,column=0,columnspan=3,pady=(0,12))
        for i,(n,s) in enumerate(PLATFORMS.items()):
            ctk.CTkLabel(chips,text=f"{s} {n}",font=("Segoe UI",9),fg_color=BG_SURFACE,corner_radius=20,text_color=TEXT_MUTED,padx=8,pady=3).grid(row=0,column=i,padx=2)
        # Queue header
        qhdr=ctk.CTkFrame(parent,fg_color="transparent"); qhdr.grid(row=1,column=0,sticky="ew"); qhdr.columnconfigure(0,weight=1)
        ctk.CTkLabel(qhdr,text="Downloads",font=("Segoe UI",13,"bold"),text_color=TEXT_PRIMARY).grid(row=0,column=0,sticky="w",pady=(0,5))
        self.q_count=ctk.CTkLabel(qhdr,text="",font=("Segoe UI",11),text_color=TEXT_MUTED); self.q_count.grid(row=0,column=1)
        ctk.CTkButton(qhdr,text="Clear",width=58,height=28,fg_color="transparent",hover_color=BG_HOVER,text_color=TEXT_MUTED,corner_radius=6,font=("Segoe UI",10),command=self._clear_queue).grid(row=0,column=2)
        self.q_scroll=ctk.CTkScrollableFrame(parent,fg_color="transparent",scrollbar_button_color=BG_SURFACE,scrollbar_button_hover_color=ACCENT_DARK); self.q_scroll.grid(row=2,column=0,sticky="nsew"); self.q_scroll.columnconfigure(0,weight=1)
        self._show_empty()

    def _show_empty(self):
        self._empty_lbl=ctk.CTkLabel(self.q_scroll,text="No downloads yet\n\nPaste a URL above and click  ⬇ Download",font=("Segoe UI",13),text_color=TEXT_MUTED,justify="center"); self._empty_lbl.grid(row=0,column=0,pady=50)

    def _paste_url(self):
        try: self.url_var.set(self.clipboard_get().strip())
        except: pass

    def _add_download(self):
        if not tools_ready(): messagebox.showwarning("Setup","Tools not ready yet — please wait."); return
        url=self.url_var.get().strip()
        if not url: messagebox.showwarning("No URL","Please paste a video URL first."); return
        self.url_var.set(""); self._enqueue(url,self.quality_var.get())

    def _add_batch(self):
        if not tools_ready(): messagebox.showwarning("Setup","Tools not ready yet."); return
        text=self.batch_txt.get("1.0","end").strip()
        if not text: return
        urls=[u.strip() for u in text.splitlines() if u.strip()]; self.batch_txt.delete("1.0","end")
        for u in urls: self._enqueue(u,self.quality_var.get())

    def _enqueue(self,url,quality):
        try: self._empty_lbl.grid_remove()
        except: pass
        self._dl_total+=1
        idx=len(self.q_scroll.winfo_children())
        card=DownloadCard(self.q_scroll,url=url,quality=quality,output_dir=self.cfg["output_dir"],on_done=self._on_done)
        card.grid(row=idx,column=0,sticky="ew",pady=(0,6)); card.start(); self._update_status()

    def _on_done(self,success): self._dl_done+=1; self._update_status()

    def _update_status(self):
        p=self._dl_total-self._dl_done
        self.q_count.configure(text=f"{self._dl_done}/{self._dl_total} done" if p>0 else f"{self._dl_total} completed")

    def _clear_queue(self):
        for w in self.q_scroll.winfo_children(): w.destroy()
        self._dl_total=self._dl_done=0; self.q_count.configure(text=""); self._show_empty()

    def _run_setup(self): SetupWizard(self,self._on_setup_done)
    def _on_setup_done(self): self.cfg["setup_done"]=True; save_config(self.cfg)


if __name__=="__main__":
    app=VideoVaultApp()
    app.mainloop()
