# macOS Extensions

A collection of useful macOS Automator workflows that add context menu options to Finder for quick access to development tools and media management.

## Quick Installation

1. **Clone this repository:**

   ```shell
   git clone https://github.com/evan-kinney/macos-extensions.git
   ```

2. **Install the workflows:**
   - Double-click each `.workflow` file you want to use
   - Click "Install" when prompted
   - The services will appear in Finder's context menu

## Detailed Installation Instructions

### Open in Visual Studio Code

**Requirements:**

- Visual Studio Code must be installed

**Installation:**

1. Double-click `Open in Visual Studio Code.workflow`
2. Click "Install" when prompted

**Usage:**

1. Right-click any file or folder in Finder
2. Select "Quick Actions" → "Open in Visual Studio Code"

### Open in iTerm

**Requirements:**

- iTerm must be installed (download from <https://iterm2.com>)

**Installation:**

1. Double-click `Open in iTerm.workflow`
2. Click "Install" when prompted

**Usage:**

1. Right-click any folder in Finder
2. Select "Quick Actions" → "Open in iTerm"

### Add to Apple Music

**Requirements:**

- Apple Music
- Python 3
- Internet connection for metadata lookup

**Installation:**

1. Double-click `Add to Apple Music.workflow`
2. Click "Install" when prompted

3. (Optional) Get a free AcoustID API key from [AcoustID](https://acoustid.org/api-key)

4. (Optional) Set the API key as an environment variable for better metadata accuracy:

   ```shell
   echo 'export ACOUSTID_API_KEY="your-api-key-here"' >> ~/.zshrc
   source ~/.zshrc
   ```

The workflow will automatically create a Python virtual environment at `~/.local/venvs/add-to-apple-music` and install required dependencies on first run.

**Usage:**

1. Right-click on an MP3 or M4A file in Finder
2. Select "Services" → "Add to Apple Music"
3. The workflow will:
   - Analyze the audio file using AcoustID fingerprinting
   - Fetch metadata from MusicBrainz
   - Update the file's ID3/MP4 tags (title, artist, album, date)
   - Move it to `~/Music/Music/Media.localized/Automatically Add to Music.localized`
4. The file will automatically appear in Apple Music

**Features:**

- Generates metadata for MP3 and M4A files using AcoustID fingerprinting and MusicBrainz
- Automatically tags files with title, artist, album, and release date
- Moves files to Apple Music's automatic import directory
- Handles duplicate filenames automatically
- Automatically creates virtual environment and installs dependencies on first run
- Shows confirmation dialog with metadata before importing

**Notes:**

- The AcoustID API key is optional but highly recommended for better metadata accuracy
- Only MP3 and M4A files are supported
- Metadata matches with confidence scores below 0.5 are skipped to ensure accuracy
- First run may take longer as it sets up the Python environment
- Virtual environment is created at `~/.local/venvs/add-to-apple-music`

**Dependencies:**

- `pyacoustid` - Audio fingerprinting
- `musicbrainzngs` - MusicBrainz API client
- `mutagen` - Audio metadata editing

**Troubleshooting:**

If metadata lookup fails:

- Check your internet connection
- Verify your AcoustID API key is set correctly
- The file may not be in the AcoustID database

## License

See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! If you'd like to contribute, please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.
