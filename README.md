# Luna Kit
This is a toolkit that is used for reading files from the My Little Pony Magic Princess Gameloft game.

# Installation
You can install Luna Kit by first making sure [python](https://python.org) (version 3.11 and later), and [git](https://git-scm.com/) is installed, then run

```shell
pip install luna-kit[cli]@git+https://github.com/ego-lay-atman-bay/luna-kit
```

To update, run this command.

```shell
pip install --upgrade luna-kit[cli]@git+https://github.com/ego-lay-atman-bay/luna-kit --force
```

# Usage

You can use Luna Kit by running

```shell
luna-kit -h
```

If that doesn't work, use `python -m luna_kit` instead of `luna-kit` (if you're on windows, you can use `py` instead of `python`).

### Downloading assets and `.ark` files

You can get the `.ark` files from your android device (in `/Android/data/com.gameloft.ANMP.GloftPOHM/files`) or download the `.ark` files directly (including ones that aren't downloaded by the game).

To download `.ark` files use the `download` command.

```shell
luna-kit download --version 10.4.1a -o "ark files/"
```

Make sure to set the `--version` argument to the version you want to download.

By default it will only download the same ones that the android game downloads (in addition to the one in the apk), however you can specify some arguments to change which files it downloads.

Options with `{}` are the defaults.

- `-c, --calibre [low,high,{veryhigh},all] ...` 
- `-t, --tag [{mlpextra,mlpdata,mlpextragui,mlpextra2,softdlc},video] ...`
- `-f, --files [all,{ark},arkdiff,other] ...`
- `-a, --astc-manifest` Download from astc_dlc_manifest (main android manifest)
- `-d, --dlc-manifest` Download from dlc_manifest (ios manifest and alternative android files)
- `--dry-run` Only print files that would be downloaded

So to download every single file, run

```shell
luna-kit download --version 10.4.1a -o "ark files/" -d -a -c all -f all
```

You can also specify the platform between `android` and `ios` (it defaults to `android`). You can download every single ark file, including the one in the apk from the server, however you can't download the ark files in the ipa for ios (which have everything except the `softdlc` ark files).

```shell
luna-kit download --version 10.4.1a -p ios -o "ark files/"
```

## Dumping `.ark` files

You can use the `dump` command to extract the `.ark` files, convert files to easily usable files, and formats json and xml files for easy readability. This command is just a combination of the later commands. This is pretty much the only command you really need when extracting `.ark` files, but the later commands are still there in case you ever need to do only one step.

To use the `dump` command just run

```shell
luna-kit dump "ark files/*.ark" -o "extracted"
```

You can also extract each file into its own folder

```shell
luna-kit dump "ark files/*.ark" -o "extracted/{name}"
```

If you omit the `-o/--output` argument, it will default to extracting each ark file into a folder with the same name in the same folder.

## Extracting `.ark` files

Extract `.ark` files with this command

```shell
luna-kit ark "path/to/ark.ark" -o "output/folder"
```

This also accepts multiple `.ark` files.

```shell
luna-kit ark "path/to/ark.ark" "another_ark.ark" -o "output"
```

The filename can also be a glob pattern (selects all the `.ark` files in a folder).

```shell
luna-kit ark "path/to/*.ark" -o "output"
```

## Split `.texatlas` files

You can split `.texatlas` files using this command.

```shell
luna-kit atlas path/to/file.texatlas -o output
```

You can leave `-o output` off to get the images in the location that they are in the game.

## Convert `.loc` files to json

`.loc` files are localization files that contain every string used in the game in each language. These can be converted to a json file just by running

```shell
luna-kit loc "english.loc"
```

And this will save `english.json`.

You can also output csv files

```shell
luna-kit loc "english.loc" --format csv
```

## Development

If you are writing a script that uses luna-kit, it is important to know all the optional dependencies (the text in brackets at the end of the installation requirement, like `luna-kit[cli]`). Multiple can also be specified `luna-kit[ark,xml,pvr,rk]`.

- `[ark]`: Required for reading `.ark` files
- `[loc]`: Required for reading `.loc` files (ok, there's no dependencies for this)
- `[audio]`: Required for reading audio files (just installed `vxn-py` and `filetype`)
- `[xml]`: Required for reading xml files
- `[texatlas]`: Required for reading `.texatlas` files
- `[pvr]`: Required for reading `.pvr` files
- `[model]`: Required for reading `.rk` and `.anim` files (and for doing transformations)
- `[rk]`: Barebones requirements for reading `.rk` and `.anim` files
- `[download]`: Everything needed to downloaded ark files
- `[cli]`: Everything needed to run the cli
- `[all]`: Includes Everything but the cli specific stuff (`rich`)

# Converting audio

The audio files are stored in `mpc` files. They can be converted to `wav` using ffmpeg, however the quality is not very good. To get the best quality conversion, use the official Musepack `mpcdec` command line utility, which is actually what the game uses. It can be downloaded at https://www.musepack.net/.

There are also some `vxn` files, which are files that contain multiple audio streams. You can use [vxn-py](https://github.com/ego-lay-atman-bay/vxn-py) to extract all the audio streams to audio files.

# Credits
- I got the information about v1 ark files from [Pony3Ark](https://github.com/Arzaroth/Pon3Ark).
- Most of the code to read v3 ark files is based off of [Celestia's ARK](https://gist.github.com/liamwhite/ba39ce769424b53a5505).

The major inspiration for creating this, was to eliminate the compilation step in Celestia's ARK, as well as providing an easy to use api. I called this "Luna Kit", because it's a toolkit for reading (and writing some) files inside My Little Pony Magic Princess, including `.ark` files, splitting `.texatlas` files, converting `.loc` files to json, etc.
