# Luna Kit
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/C0C61YMJCH)

This is a toolkit that is used for reading files from the My Little Pony Magic Princess Gameloft game.

# Installation

## uv

The easiest way to install and update luna kit, is by using [uv](https://docs.astral.sh/uv/). After you have uv installed, run this command to install Luna Kit.

```shell
uv tool install 'git+https://github.com/ego-lay-atman-bay/luna-kit[cli]'
```

And then you can use `luna-kit` globally.

To update, just run

```shell
uv tool upgrade 'luna-kit[cli]'
```

To uninstall, just run

```shell
uv tool uninstall luna-kit
```

## pip

If you need to install it through pip, just run this command.

```shell
pip install luna-kit[cli]@git+https://github.com/ego-lay-atman-bay/luna-kit
```

To update, run this command.

```shell
pip install --upgrade luna-kit[cli]@git+https://github.com/ego-lay-atman-bay/luna-kit --force
```

And uninstalling

```shell
pip uninstall lun-kit
```

## Tab Autocompletion (optional)

If you would like tab autocompletion, this program uses [argcomplete](https://kislyuk.github.io/argcomplete/), so all you need to do is set that up (you can ignore the python code stuff).

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

The `dump` command will do everything below automatically, so you don't need to bother with them.

## The `ark` command

The `ark` command has several subcommands to help with different operations on ark files.

## List files

You can list all the files in an ark file with the `list` subcommand.

```shell
luna-kit list test.ark
```
```
test.ark
file.json 2026-05-06 00:02:58
...
```

### Extracting

You can extract ark files easily with the `extract` subcommand. Note, unlike `dump`, this does not modify the files in any way (so many files may not be human readable).

```shell
luna-kit ark extract "files/*.ark" "other.ark" -o "extracted"
```

## Create and add to ark files

> [!NOTE]
> While luna kit does have the ability to create and modify ark files, I will not be showing you how to load them in the game, you'll have to figure it out yourself.

You can also create and add to ark files. Both the `create` and `add` subcommands work practically the same, the only difference is that `create` completely overrides the output file if it already exists, while `add` just adds to it.

```shell
luna-kit ark create input.txt other.txt=folder/other.txt folder/ -o test.ark
```

You can add both single files or entire folders. Right now there is no system to automatically reverse what the `dump` command outputs.

When you put a direct path to a filename, it only uses the base name (for example, `test.txt` from `folder/test.txt`). However, you can optionally specify the filename you want to be used in the ark file with `=filename.txt`.

When you specify a folder, it adds all files in the folder recursively. All the filenames used will relative to the input folder, so subfolders keep their structure. You can also add `=folder` to put all the files in a specific folder in the ark file instead of the root directory.

When the game loads ark files, it uses the file that has the latest timestamp whenever there are duplicates across multiple ark files. Due to this, luna kit automatically uses the current date when adding files to ark files. If you wish to use the modified date on your device instead, you can add the `-t/--use-system-timestamps` flag to the command.

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

## `.swf` files

Luna Kit provides a `swf` command to easily convert swf files to animated webp files and fix images. This command is made specifically for the animated avatars, so don't expect anything else to work.

Before you run the command, you need to first install both [ffmpeg](https://ffmpeg.org/) and [JPEX](https://github.com/jindrapetrik/jpexs-decompiler).

Ffmpeg can be installed normally, but must be available on the PATH. However JPEX is a little different. If installing it normally doesn't add `ffdec` to the PATH, then you need to download the zip, specifically look for **"ZIP (Windows, Linux, Mac OS)"** in the github releases. Then unzip it and either add the folder to the PATH, or provide `--ffdec path/to/ffdec.jar` in the command.

```shell
luna-kit swf render pa_495702.swf -o pa_495702.webp --ffdec path/to/ffdex.jar
```

## Development

If you are writing a script that uses luna kit, it is important to know all the optional dependencies (the text in brackets at the end of the installation requirement, like `luna-kit[cli]`). Multiple can also be specified `luna-kit[ark,xml,pvr,rk]`.

- `[ark]`: Required for reading `.ark` files
- `[loc]`: Required for reading `.loc` files (ok, there's no dependencies for this)
- `[audio]`: Required for reading audio files (just installs `vxn-py` and `filetype`)
- `[xml]`: Required for reading xml files
- `[texatlas]`: Required for reading `.texatlas` files
- `[pvr]`: Required for reading `.pvr` files
- `[model]`: Required for reading `.rk` and `.anim` files (and for doing transformations)
- `[rk]`: Barebones requirements for reading `.rk` and `.anim` files
- `[download]`: Everything needed to downloaded ark files
- `[cli]`: Everything needed to run the cli
- `[all]`: Includes Everything except cli specific stuff (`rich`)

The main reason the dependencies are split up like this, is to reduce bundle size if you are just using one thing. For example, if you're just writing a script to read `.rk` files, you don't need any networking stuff that's needed for `download`. You especially don't need the massive `rich` library if you're not using the cli.

# Converting audio

The audio files are stored in `mpc` files. They can be converted to `wav` using ffmpeg, however the quality is not very good. To get the best quality conversion, use the official Musepack `mpcdec` command line utility, which is actually what the game uses. It can be downloaded at https://www.musepack.net/.

There are also some `vxn` files, which are files that contain multiple audio streams. You can use [vxn-py](https://github.com/ego-lay-atman-bay/vxn-py) to extract all the audio streams to audio files.

# Credits
- I got the information about v1 ark files from [Pony3Ark](https://github.com/Arzaroth/Pon3Ark).
- Most of the code to read v3 ark files is based off of [Celestia's ARK](https://gist.github.com/liamwhite/ba39ce769424b53a5505).

The major inspiration for creating this, was to eliminate the compilation step in Celestia's ARK, as well as providing an easy to use api. I called this "Luna Kit", because it's a toolkit for reading (and writing some) files inside My Little Pony Magic Princess, including `.ark` files, splitting `.texatlas` files, converting `.loc` files to json, etc.
