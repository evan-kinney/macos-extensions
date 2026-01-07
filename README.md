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

### Open in GitHub Desktop

Right-click any folder in Finder → "Quick Actions" → "Open in GitHub Desktop"

### Open in IntelliJ IDEA CE

Right-click any file or folder in Finder → "Quick Actions" → "Open in IntelliJ IDEA CE"

### Open in iTerm

**Requirements:**

### Open in Visual Studio Code

Right-click any file or folder in Finder → "Quick Actions" → "Open in Visual Studio Code"

## Installation

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

### Copy to Server

**Requirements:**

- Python 3 (install with `brew install python@3.14 python-tk@3.14 && brew link --overwrite python@3.14`)
- SSH access to at least one server configured in `~/.ssh/config`
- For password authentication: `sshpass` (install with `brew install sshpass`)

**Installation:**

1. Double-click `Copy to Server.workflow`
2. Click "Install" when prompted

The workflow will automatically create a Python virtual environment at `~/.local/venvs/copy-to-server` on first run.

**Usage:**

1. Right-click on any file(s) or folder(s) in Finder
2. Select "Quick Actions" → "Copy to Server"
3. The workflow will:
   - Display a dialog with servers from your SSH config
   - Allow you to select a destination path with autocomplete
   - Prompt for a password if needed (no SSH key or key requires passphrase)
   - Copy the selected files to the remote server via SCP

**Features:**

- Parses `~/.ssh/config` to populate server dropdown
- Supports SSH key authentication (IdentityFile)
- Supports password authentication (requires `sshpass`)
- Dynamic destination path autocomplete via SSH
- Handles multiple file/folder selections
- Dark mode support for dialog interface
- Progress feedback and error handling

**SSH Config Setup:**

Your `~/.ssh/config` should contain entries like:

```ssh
Host myserver
  HostName 192.168.1.100
  User username
  IdentityFile ~/.ssh/id_rsa
```

**Notes:**

- For password authentication without an SSH key, install `sshpass`: `brew install sshpass`
- The destination path autocomplete queries directories on the remote server
- Default destination suggestions include: `~/`, `~/Desktop/`, `~/Documents/`, `~/Downloads/`
- Wildcards (`*`, `?`) in SSH config Host entries are ignored

**Dependencies:**

- `tkinter` - GUI dialogs (included with Python on macOS)

**Troubleshooting:**

If copy fails:

- Verify your SSH config is correctly formatted
- Test SSH connection manually: `ssh <hostname>`
- For password auth, ensure `sshpass` is installed
- Check file permissions on the destination server
- Verify network connectivity to the remote server

## License

See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! If you'd like to contribute, please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.