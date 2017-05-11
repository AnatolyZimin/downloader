# downloader

Just small utility to download files.

## Requirements

* Python 3.6+

## How to install dependencies

    pip install -r requirements.txt

## How to use

    python downloader.py --help
    
## How to extend

There is base class called `BaseAdapter` in [`requests` package](http://docs.python-requests.org/) and its default implementation called `HTTPAdapter`. The latter is used to download files over HTTP and HTTPS.

To add support of other protocols, such as FTP and so on, you have to implement your own class based on `BaseAdapter` and follow [this instructions](http://docs.python-requests.org/en/master/user/advanced/#transport-adapters) to customize `Session` instance which then must be provided as `session` argument when creating an instance of `Downloader`. Also you can modify session property of existing `Downloader` instance.
