# Luna Kit
This is a toolkit that is used for reading files from the My Little Pony Magic Princess Gameloft game. Currently it can only extract `.ark` files, but later may add more functionality.

# Installation
You can install Luna Kit by first making sure [python](https://python.org) is installed, then run.

```
pip install git+https://github.com/ego-lay-atman-bay/luna-kit
```

To update, run this command.

```
pip install --upgrade git+https://github.com/ego-lay-atman-bay/luna-kit --force
```

# Usage

You can use Luna Kit by running

```
luna-kit -h
```

If that doesn't work, use `python -m luna_kit` instead of `luna-kit` (if you're on windows, you can use `py` instead of `python`).

## Extracting `.ark` files

Extract `.ark` files with this command

```
luna-kit ark "path/to/ark.ark" -o "output/folder"
```

This also accepts multiple `.ark` files.

```
luna-kit ark "path/to/ark.ark" "another_ark.ark" -o "output"
```

The filename can also be a glob pattern

```
luna-kit ark "path/to/*.ark" -o "output"
```

## Split `.texatlas` files

You can split `.texatlas` files using

```
luna-kit atlas path/to/file.texatlas -o output
```

## Convert `.loc` files to json

`.loc` files are localization files that contain every string used in the game in each language. These can be converted to a json file just by running

```
luna-kit loc "english.loc"
```

And this will save `english.json`. Note that some languages, like chinese, will have special characters encoded, so you'll probably have to open the json file with some json parser to get the special characters.

# Credits
This project is based off of [Celestia's Ark](https://gist.github.com/liamwhite/ba39ce769424b53a5505), in fact, a lot of the `.ark` file reading code was taken from Celestia's Ark (just rewritten in python).

The major inspiration for creating this, was to eliminate the compile step in Celestia's Ark, as well as providing an easy to use api. I called this "Luna Kit", because I'm planning on doing more than just extracting `.ark` file (maybe writing to them?).
