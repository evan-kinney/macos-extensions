#!/usr/bin/env python3
"""
Add to Apple Music Workflow Script
Generates metadata for audio files using AcoustID and MusicBrainz,
then moves them to the Apple Music automatic import directory.
"""

import os
import sys
import shutil
import subprocess
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

import acoustid
import musicbrainzngs
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
from mutagen.id3 import ID3NoHeaderError


# Configure MusicBrainz
musicbrainzngs.set_useragent(
    "macOS-Add-to-Apple-Music",
    "1.0",
    "https://github.com/evan-kinney/macos-extensions"
)

# Apple Music automatic import directory
MUSIC_IMPORT_DIR = os.path.expanduser(
    "~/Music/Music/Media.localized/Automatically Add to Music.localized"
)


class MetadataDialog:
    """Custom dialog for editing metadata with retry functionality."""
    
    def get_border_color(self):
        """Detect if system is in dark mode and return appropriate border color."""
        try:
            # Run AppleScript to detect dark mode on macOS
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to tell appearance preferences to get dark mode'],
                capture_output=True,
                text=True,
                timeout=1
            )
            is_dark_mode = result.stdout.strip().lower() == 'true'
            
            # Light color for dark mode, dark color for light mode
            return '#666666' if is_dark_mode else '#CCCCCC'
        except Exception as e:
            print(f"Could not detect appearance mode: {e}")
            # Default to a neutral gray
            return '#999999'
    
    def __init__(self, title, artist, album, date, filename):
        self.result = None
        self.action = None
        
        self.root = tk.Tk()
        self.root.title("Add to Apple Music")
        
        # Set window properties
        self.root.geometry("500x200")
        self.root.resizable(False, False)
        
        # Bring window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Detect dark mode
        border_color = self.get_border_color()
        
        # Create main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create entry fields
        self.entries = {}
        fields = [
            ('Title', title or 'Unknown'),
            ('Artist', artist or 'Unknown'),
            ('Album', album or 'Unknown'),
            ('Date', date or '')
        ]
        
        for label_text, default_value in fields:
            frame = tk.Frame(main_frame)
            frame.pack(fill=tk.X, pady=2)
            
            label = tk.Label(frame, text=label_text, width=6, anchor=tk.W, font=("Helvetica", 10, "bold"))
            label.pack(side=tk.LEFT)
            
            entry = tk.Entry(frame, width=40, relief=tk.SOLID, borderwidth=1, highlightthickness=1, highlightbackground=border_color, highlightcolor=border_color)
            entry.insert(0, default_value)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.entries[label_text.lower()] = entry
        
        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=(20, 0), anchor=tk.E)
        
        # Buttons
        tk.Button(button_frame, text="Cancel", 
                 command=self.cancel).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Import", 
                 command=self.import_file, default=tk.ACTIVE).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to Import
        self.root.bind('<Return>', lambda e: self.import_file())
        self.root.bind('<Escape>', lambda e: self.cancel())
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def get_metadata(self):
        """Get current metadata from entry fields."""
        return {
            'title': self.entries['title'].get() or None,
            'artist': self.entries['artist'].get() or None,
            'album': self.entries['album'].get() or None,
            'date': self.entries['date'].get() or None
        }
    
    def cancel(self):
        """Cancel the operation."""
        self.action = 'cancel'
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def import_file(self):
        """Import with current metadata."""
        self.action = 'import'
        self.result = self.get_metadata()
        self.root.quit()
        self.root.destroy()
    
    def show(self):
        """Show the dialog and return the result."""
        self.root.mainloop()
        return self.action, self.result


def show_editable_metadata_dialog(title, artist, album, date, filename):
    """Show a native Python dialog with editable metadata fields."""
    try:
        dialog = MetadataDialog(title, artist, album, date, filename)
        action, metadata = dialog.show()
        
        if action == 'import':
            return True, metadata
        else:
            return False, None
            
    except Exception as e:
        print(f"Error showing dialog: {e}")
        # Fallback to terminal input
        print(f"\nFile: {filename}")
        print(f"Title: {title or 'Unknown'}")
        print(f"Artist: {artist or 'Unknown'}")
        print(f"Album: {album or 'Unknown'}")
        print(f"Date: {date or ''}")
        response = input("Import this file? (y/n): ").lower()
        if response == 'y':
            return True, {
                'title': title,
                'artist': artist,
                'album': album,
                'date': date
            }
        return False, None


def search_musicbrainz_by_metadata(title=None, artist=None, album=None):
    """Search MusicBrainz using metadata fields to find matching recordings."""
    try:
        # Build search query
        query_parts = []
        if title:
            query_parts.append(f'recording:"{title}"')
        if artist:
            query_parts.append(f'artist:"{artist}"')
        if album:
            query_parts.append(f'release:"{album}"')
        
        if not query_parts:
            return None
        
        query = ' AND '.join(query_parts)
        
        # Search for recordings
        result = musicbrainzngs.search_recordings(query=query, limit=5)
        
        if result.get('recording-list'):
            recordings = result['recording-list']
            # Return the best match (first result)
            if recordings:
                recording = recordings[0]
                metadata = {
                    'title': recording.get('title', ''),
                    'artist': recording['artist-credit-phrase'] if 'artist-credit-phrase' in recording else '',
                }
                
                # Get album information if available
                if 'release-list' in recording and len(recording['release-list']) > 0:
                    release = recording['release-list'][0]
                    metadata['album'] = release.get('title', '')
                    metadata['date'] = release.get('date', '')
                
                return metadata
        
        return None
    except Exception as e:
        print(f"Error searching MusicBrainz: {e}")
        return None


def show_confirmation_dialog(title, artist, album, date, filename):
    """Show a native macOS dialog asking for confirmation to import the file."""
    # This is kept for backward compatibility but now uses the editable dialog
    action, metadata = show_editable_metadata_dialog(title, artist, album, date, filename)
    
    if action == 'import':
        return True, metadata
    elif action == 'retry':
        return 'retry', metadata
    else:
        return False, None


def get_acoustid_fingerprint(file_path):
    """Generate AcoustID fingerprint for the audio file."""
    try:
        # You'll need an AcoustID API key - get one from https://acoustid.org/api-key
        # For now, we'll use a placeholder - users should set ACOUSTID_API_KEY env variable
        api_key = os.environ.get('ACOUSTID_API_KEY', '')
        
        if not api_key:
            print("Warning: ACOUSTID_API_KEY not set. Metadata lookup may be limited.")
            print("Get your API key from: https://acoustid.org/api-key")
            return None
        
        results = acoustid.match(api_key, file_path)
        return list(results)
    except Exception as e:
        print(f"Error getting AcoustID fingerprint: {e}")
        return None


def get_metadata_from_musicbrainz(recording_id):
    """Fetch metadata from MusicBrainz using recording ID with retry logic."""
    max_retries = 5
    retry_delay = 1  # Start with 1 second delay
    
    for attempt in range(max_retries):
        try:
            result = musicbrainzngs.get_recording_by_id(
                recording_id,
                includes=['artists', 'releases', 'artist-credits']
            )
            recording = result['recording']
            
            metadata = {
                'title': recording.get('title', ''),
                'artist': recording['artist-credit-phrase'] if 'artist-credit-phrase' in recording else '',
            }
            
            # Get album information if available
            if 'release-list' in recording and len(recording['release-list']) > 0:
                release = recording['release-list'][0]
                metadata['album'] = release.get('title', '')
                metadata['date'] = release.get('date', '')
            
            return metadata
        except Exception as e:
            error_msg = str(e)
            # Check if it's a connection error that we should retry
            if any(err in error_msg.lower() for err in ['connection reset', 'urlopen error', 'connection error', 'timeout']):
                if attempt < max_retries - 1:
                    print(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"Error fetching MusicBrainz metadata after {max_retries} attempts: {e}")
                    return None
            else:
                # For non-connection errors, don't retry
                print(f"Error fetching MusicBrainz metadata: {e}")
                return None
    
    return None


def update_mp3_metadata(file_path, metadata):
    """Update MP3 file metadata using ID3 tags."""
    try:
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            audio = EasyID3()
            audio.save(file_path)
            audio = EasyID3(file_path)
        
        if metadata.get('title'):
            audio['title'] = metadata['title']
        if metadata.get('artist'):
            audio['artist'] = metadata['artist']
        if metadata.get('album'):
            audio['album'] = metadata['album']
        if metadata.get('date'):
            audio['date'] = metadata['date']
        
        audio.save()
        print(f"Updated MP3 metadata: {metadata.get('title', 'Unknown')} - {metadata.get('artist', 'Unknown')}")
        return True
    except Exception as e:
        print(f"Error updating MP3 metadata: {e}")
        return False


def update_m4a_metadata(file_path, metadata):
    """Update M4A file metadata using MP4 tags."""
    try:
        audio = MP4(file_path)
        
        if metadata.get('title'):
            audio['\xa9nam'] = metadata['title']
        if metadata.get('artist'):
            audio['\xa9ART'] = metadata['artist']
        if metadata.get('album'):
            audio['\xa9alb'] = metadata['album']
        if metadata.get('date'):
            audio['\xa9day'] = metadata['date']
        
        audio.save()
        print(f"Updated M4A metadata: {metadata.get('title', 'Unknown')} - {metadata.get('artist', 'Unknown')}")
        return True
    except Exception as e:
        print(f"Error updating M4A metadata: {e}")
        return False


def process_audio_file(file_path):
    """Process a single audio file: add metadata and move to Music import directory."""
    print(f"\nProcessing: {file_path}")
    
    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    # Check file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ['.mp3', '.m4a']:
        print(f"Error: Unsupported file type: {file_ext}")
        return False
    
    # Variables to store metadata for confirmation dialog
    confirmed_metadata = None
    filename = os.path.basename(file_path)
    
    # Get AcoustID fingerprint and metadata
    acoustid_results = get_acoustid_fingerprint(file_path)
    
    # Initial metadata from AcoustID
    initial_metadata = None
    
    if acoustid_results:
        # Process the best match
        for score, recording_id, title, artist in acoustid_results:
            print(f"Found match (score: {score:.2f}): {title} - {artist}")
            
            if score > 0.5:  # Only use matches with reasonable confidence
                # Get detailed metadata from MusicBrainz
                initial_metadata = get_metadata_from_musicbrainz(recording_id)
                break
            else:
                print("Match score too low, skipping metadata update")
                break
    
    # If no metadata found, start with unknown values
    if not initial_metadata:
        print("No AcoustID match found")
        initial_metadata = {
            'title': 'Unknown',
            'artist': 'Unknown',
            'album': 'Unknown',
            'date': ''
        }
    
    # Show dialog with metadata
    user_confirmed, confirmed_metadata = show_confirmation_dialog(
        initial_metadata.get('title', 'Unknown'),
        initial_metadata.get('artist', 'Unknown'),
        initial_metadata.get('album', 'Unknown'),
        initial_metadata.get('date', ''),
        filename
    )
    
    if not user_confirmed:
        print("User cancelled import")
        return False
    
    # Update file metadata based on file type
    if confirmed_metadata:
        if file_ext == '.mp3':
            update_mp3_metadata(file_path, confirmed_metadata)
        elif file_ext == '.m4a':
            update_m4a_metadata(file_path, confirmed_metadata)
    
    # Create Music import directory if it doesn't exist
    os.makedirs(MUSIC_IMPORT_DIR, exist_ok=True)
    
    # Move file to Music import directory
    destination = os.path.join(MUSIC_IMPORT_DIR, filename)
    
    # Handle duplicate filenames
    if os.path.exists(destination):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(destination):
            destination = os.path.join(MUSIC_IMPORT_DIR, f"{base}_{counter}{ext}")
            counter += 1
    
    try:
        shutil.move(file_path, destination)
        print(f"Moved to: {destination}")
        print("File will be automatically imported to Apple Music")
        return True
    except Exception as e:
        print(f"Error moving file: {e}")
        return False


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: add_to_music.py <audio_file> [audio_file ...]")
        sys.exit(1)
    
    # Process each file passed as argument
    success_count = 0
    for file_path in sys.argv[1:]:
        if process_audio_file(file_path):
            success_count += 1
    
    print(f"\nProcessed {success_count} of {len(sys.argv) - 1} file(s) successfully")
    
    if success_count > 0:
        print("\nNote: Files have been moved to the Apple Music automatic import directory.")
        print("They should appear in your Music library shortly.")


if __name__ == "__main__":
    main()
