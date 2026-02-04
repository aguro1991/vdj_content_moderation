# Content Moderation Instructions for Music Files

## Overview
Analyze song lyrics and assign content ratings based on the presence of flagged words.

## Word Lists Location
- **Slurs**: `~/github/vdj_content_moderation/lists/slurs.yaml`
- **Sexual Content**: `~/github/vdj_content_moderation/lists/sexual-content.yaml`
- **Severe Swear Words**: `~/github/vdj_content_moderation/lists/severe-swear-words.yaml`
- **Other Swear Words**: `~/github/vdj_content_moderation/lists/other-swear-words.yaml`

## Rating System (in order of severity)
Assign the **highest applicable rating** based on words found:

| Rating | Triggered By | Word List |
|--------|--------------|-----------|
| **X** | Slurs or variations | slurs.yaml |
| **R** | Sexual content words or variations | sexual-content.yaml |
| **PG-13** | Severe swear words or variations | severe-swear-words.yaml |
| **PG-8** | Other swear words or variations | other-swear-words.yaml |
| **G** | No flagged words found | N/A |

## Default Parameters
- **Music directory**: `~/Music/DJing/Music/WCS/`
- **Count**: 20 songs

## Process

### Step 1: Select Songs
- Select 20 random songs from `~/Music/DJing/Music/WCS/` that are eligible for rating
- Use the following approach:
  1. List all music files in the directory
  2. For each file, check if it has an `AI Content Rating Date:` in the comment tag
  3. Build a list of **eligible songs**: songs that either have NO content rating date, OR have a content rating date older than 30 days
   4. From the eligible songs list, select up to 20 songs with the oldest rating dates first (songs with no rating date are treated as oldest)
- **Command to check existing rating date**:
  ```bash
  ffprobe -v quiet -show_entries format_tags=comment -of default=noprint_wrappers=1:nokey=1 "<filepath>"
  ```
  Then parse for `AI Content Rating Date: YYYY-MM-DD` and compare to current date
- A song is eligible if:
  - No `AI Content Rating Date:` exists in the comment, OR
  - The `AI Content Rating Date:` is more than 30 days ago

#### Song Selection Script
Use this Python script to find eligible songs:
```python
import subprocess
import os
import re
from datetime import datetime, timedelta

music_dir = os.path.expanduser("~/Music/DJing/Music/WCS/")
thirty_days_ago = datetime.now() - timedelta(days=30)

# Get all music files
result = subprocess.run(
    ["find", music_dir, "-type", "f", "(", "-name", "*.mp3", "-o", "-name", "*.m4a", "-o", "-name", "*.MP3", "-o", "-name", "*.M4A", "-o", "-name", "*.aiff", "-o", "-name", "*.AIFF", ")"],
    capture_output=True, text=True
)
all_files = result.stdout.strip().split('\n')

# List of (filepath, rating_date) tuples - None date means never rated
eligible = []
for filepath in all_files:
    if not filepath.strip():
        continue
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format_tags=comment", "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True, timeout=5
        )
        comment = result.stdout.strip()
        
        # Check for AI Content Rating Date
        match = re.search(r'AI Content Rating Date: (\d{4}-\d{2}-\d{2})', comment)
        if match:
            rating_date = datetime.strptime(match.group(1), "%Y-%m-%d")
            if rating_date > thirty_days_ago:
                continue  # Skip, rated within 30 days
            eligible.append((filepath, rating_date))
        else:
            eligible.append((filepath, None))  # Never rated
    except Exception as e:
        eligible.append((filepath, None))  # If we can't check, treat as never rated

# Sort by rating date (None/never rated first, then oldest dates)
eligible.sort(key=lambda x: (x[1] is not None, x[1] if x[1] else datetime.min))

# Select up to 20 oldest
selected = eligible[:20]
for f, _ in selected:
    print(f)
```

### Step 2: Read Word Lists
- Read all four YAML files to understand what words to search for
- Consider variations of words (e.g., plural forms, verb conjugations)

### Step 3: Search for Lyrics
- Use web search to find lyrics for each song
- Search for explicit content warnings or parental advisory information
- Do NOT reproduce copyrighted lyrics in full

#### Ensuring Complete Lyrics Retrieval
- **Always verify you have the COMPLETE lyrics** before assigning a rating
- If web search results only show excerpts or metadata (song title, credits, etc.) without actual lyrics text, you do NOT have sufficient information
- **Featured artists require extra attention**: Songs with featured artists (indicated by "feat.", "ft.", "with", etc.) often have verses by the featured artist that contain different content than the main artist. ALWAYS verify you have retrieved the featured artist's verse(s), not just the chorus and main artist verses. Slurs and explicit content frequently appear in featured rap verses.
- **Multi-source verification**: Try at least 2-3 different sources to ensure lyrics are complete:
  1. Search `"[artist] [song] lyrics"` - check Genius, AZLyrics, Musixmatch excerpts
  2. Search `"[song title] [artist] explicit lyrics"` or `"[song] swear words"` to surface any flagged content
  3. If initial searches only return metadata, search for `"[song] lyrics full text"` or `"[song] complete lyrics"`
- **Red flags that you don't have complete lyrics**:
  - Search results only show song credits, producers, album info
  - Only seeing "About" sections or song descriptions
  - Lyrics sites blocked or returning CAPTCHA pages
  - Only partial excerpts (e.g., just chorus or first verse)
  - Song has featured artist but no verse attributed to them in retrieved lyrics
  - Retrieved lyrics are suspiciously short for a 2-4 minute song
- **If you cannot obtain complete lyrics**: 
  - Assign a lower confidence score (0.60-0.75)
  - Consider searching for the song on YouTube with "[song] lyrics video" which may have lyrics in video descriptions or comments
  - Check if the song is a cover and search for the original version's lyrics
- **If NO lyrics can be found at all** (obscure artist, new release, no transcriptions exist):
  - Do NOT default to G rating
  - Assign rating `MANUAL REVIEW` instead of a letter rating
  - Set confidence to 0.00
  - In the CSV, record as: `"song.mp3",MANUAL REVIEW,0.00`
  - Do NOT write to the file's metadata - leave it unchanged so it will be picked up again
  - Flag these songs for the user to manually listen and rate
- **Never assign G rating with high confidence unless you have verified the complete lyrics**

### Step 4: Analyze Lyrics
- Check for flagged words in order of severity (slurs first, then sexual, then severe swears, then other swears)
- Stop at the highest-severity match found
- Only assign ratings based on **words actually found**, not album labels or assumptions
- **CRITICAL**: Before assigning ANY rating other than X, explicitly verify that NO slurs or slur variations are present in the lyrics. Scan the entire lyrics text for all words in slurs.yaml (including variations like plurals: "niggas" from "nigga", "faggots" from "faggot", etc.) BEFORE considering lower-severity words.
- Do NOT get distracted by R-rated or PG-13 words until you have confirmed zero slurs exist
- **IMPORTANT**: Only check the **actual lyrics text** for flagged words. Do NOT use:
  - Song descriptions or bios (e.g., Genius "About" sections)
  - User annotations or interpretations
  - Editorial commentary about what the song is "about"
  - Thematic descriptions (e.g., "this song is about X")
- If a song uses metaphorical or suggestive language but does not contain explicit flagged words, rate it G

#### Lyrics Text Verification Checklist
Before assigning ANY rating, confirm you can answer YES to this question:
- **"Did I see actual sung/rapped words from the song (verses, choruses, bridges)?"**

If your search results only contain:
- Song meaning explanations
- Historical context or background
- Producer/writer credits
- Album information
- Thematic descriptions ("this song is about freedom/love/etc.")

Then you do NOT have the lyrics. You MUST search again with different queries until you find the actual lyric text. Common queries that help:
- `"[song title]" "[artist]" lyrics site:genius.com`
- `"[song title]" "[artist]" lyrics site:azlyrics.com`
- `"[song title]" full lyrics text`

**NEVER assign a G rating based on song descriptions or themes.** A protest song about racial injustice may still contain slurs. A love song may still contain explicit language. Only the actual lyrics determine the rating.

### Step 5: Assign Confidence
- 0.90-0.95: Lyrics verified from reliable source (Genius, official)
- 0.80-0.89: Lyrics found but source less certain
- 0.60-0.79: Partial lyrics or obscure song, less verification
- 0.50-0.59: Unable to fully verify lyrics

### Step 5a: Retry Low-Confidence Searches
- If the confidence score is **below 0.70**, make a **second attempt** to find lyrics
- On the second attempt:
  1. Try alternative search queries (e.g., include album name, record label, or alternate spellings)
  2. Search for cover versions or live performances that may have transcribed lyrics
  3. Check if the song is instrumental (no lyrics = automatic G rating with high confidence)
  4. Look for the song on additional lyric sites beyond the initial search
- If the second attempt yields better results, update the confidence score accordingly
- If confidence remains below 0.70 after the retry, proceed with the best available information and note the uncertainty

### Step 6: Output to CSV
- File location: `~/amp/content.csv`
- Format: `song,rating,confidence`
- Song field should include full filename from source directory
- **Append to existing CSV** if it exists (do not overwrite previous ratings)

### Step 7: Write Rating to ID3 Comment Tag
- Use **Python with mutagen** to write the content rating to the file's comment metadata
- **Important**: Do NOT use ffmpeg for writing metadata - it writes to TXXX frames instead of proper COMM frames, which breaks compatibility with DJ software like Rekordbox
- **Format**: `AI Content Rating: <RATING>, AI Content Rating Date: <YYYY-MM-DD>, <existing comment>`
- **Position**: Rating info goes at the BEGINNING of the comment, followed by existing comments
- **Preserve existing comments**: Read the current comment field first, then prepend the rating info
- **Update existing ratings**: If `AI Content Rating:` already exists in the comment, update it instead of duplicating

#### For MP3 files (ID3 tags):
```python
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, COMM, TIT2, TPE1, TALB, TCON, TRCK, TDRC
import re

def update_mp3_comment(filepath, rating):
    audio = MP3(filepath)
    today = datetime.date.today().isoformat()
    
    # Create ID3v2 tags if none exist
    if audio.tags is None:
        audio.add_tags()
    
    # Migrate ID3v1 tags to ID3v2 if they exist but ID3v2 equivalents don't
    # ID3v1 fields are accessible via audio.tags for reading
    id3v1_mapping = {
        'TIT2': ('title', TIT2),      # Title
        'TPE1': ('artist', TPE1),     # Artist
        'TALB': ('album', TALB),      # Album
        'TCON': ('genre', TCON),      # Genre
        'TRCK': ('track', TRCK),      # Track number
    }
    
    for v2_key, (v1_attr, frame_class) in id3v1_mapping.items():
        if v2_key not in audio.tags:
            # Check if ID3v1 tag exists via the raw ID3v1 data
            if hasattr(audio, 'info') and hasattr(audio.tags, '_V1') and audio.tags._V1:
                v1_value = getattr(audio.tags._V1, v1_attr, None)
                if v1_value:
                    audio.tags.add(frame_class(encoding=3, text=v1_value))
    
    # Get existing comment from COMM frame
    existing_comment = ""
    for key in audio.tags.keys():
        if key.startswith('COMM'):
            existing_comment = str(audio.tags[key].text[0]) if audio.tags[key].text else ""
            break
    
    # Remove old AI rating if present
    remaining = re.sub(r',?\s*AI Content Rating: [A-Z0-9-]+,? AI Content Rating Date: [0-9-]+\s*,?', '', existing_comment)
    remaining = remaining.strip().strip(',').strip()
    
    # Prepend new rating
    if remaining:
        new_comment = f"AI Content Rating: {rating}, AI Content Rating Date: {today}, {remaining}"
    else:
        new_comment = f"AI Content Rating: {rating}, AI Content Rating Date: {today}"
    
    # Write proper COMM frame (lang='eng', desc='')
    audio.tags.delall('COMM')
    audio.tags.add(COMM(encoding=3, lang='eng', desc='', text=new_comment))
    
    # Save as ID3v2.4 only, removing ID3v1 tags (v1=0)
    audio.save(v1=0, v2_version=4)
```

#### For M4A/MP4 files (iTunes tags):
```python
from mutagen.mp4 import MP4
import re

def update_m4a_comment(filepath, rating):
    audio = MP4(filepath)
    today = datetime.date.today().isoformat()
    
    # Get existing comment
    existing_comment = audio.tags.get('\xa9cmt', [''])[0] if audio.tags else ''
    
    # Remove old AI rating if present
    remaining = re.sub(r',?\s*AI Content Rating: [A-Z0-9-]+,? AI Content Rating Date: [0-9-]+\s*,?', '', existing_comment)
    remaining = remaining.strip().strip(',').strip()
    
    # Prepend new rating
    if remaining:
        new_comment = f"AI Content Rating: {rating}, AI Content Rating Date: {today}, {remaining}"
    else:
        new_comment = f"AI Content Rating: {rating}, AI Content Rating Date: {today}"
    
    audio['\xa9cmt'] = new_comment
    audio.save()
```

#### Command to read current comment:
```bash
ffprobe -v quiet -show_entries format_tags=comment -of default=noprint_wrappers=1:nokey=1 "<filepath>"
```

## Example Output
```csv
song,rating,confidence
"Artist - Song Title (Album).mp3",X,0.95
"Artist - Clean Song (Album).m4a",G,0.90
```

### Step 8: Display Results Table
- After processing all songs, output a summary table to the user
- Format as a markdown table with columns: Song, Rating, Confidence
- Example:

| Song | Rating | Confidence |
|------|--------|------------|
| Artist - Song Title | G | 0.95 |
| Artist - Another Song | PG-13 | 0.90 |
| Artist - Explicit Song | X | 0.92 |

## Important Notes
1. Check for slurs FIRST - they result in the highest rating (X)
2. Do NOT rate based on album "Explicit" labels - only rate based on actual flagged words found
3. If no flagged words are found, assign G rating regardless of suggestive themes
4. Include variations of words (e.g., "bitches" matches "bitch", "fuckin" matches "fuck")
5. Skip songs that have been rated within the last 30 days to avoid redundant processing
