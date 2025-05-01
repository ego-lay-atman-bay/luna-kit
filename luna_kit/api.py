from dataclasses import dataclass
from functools import wraps
import io
from typing import BinaryIO, Callable, Generator, Literal, TypedDict, overload
import urllib
import urllib.parse

from .file_utils import PathOrBinaryFile, open_binary

try:
    from furl import furl
    import requests
except:
    raise ImportError('api dependencies could not be found')

class DataCenter(TypedDict):
    name: str
    status: Literal['status']
    preferred: bool
    country_code: str
    _datacenter_id: str

@dataclass()
class ClientID:
    game: Literal[1370] = 1370
    client_p2: Literal[51627, 51679] = 51627
    version: str = '10.2.0q'
    platform: Literal['android', 'ios'] = 'android'
    store: Literal['googleplay', 'appstore'] = 'googleplay'
    
    @classmethod
    def new(cls, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], ClientID):
                return cls(
                    game = args[0].game,
                    client_p2 = args[0].client_p2,
                    version = args[0].version,
                    platform = args[0].platform,
                    store = args[0].store,
                )
            else:
                return cls(*args[0].split(':'))
        elif len(args) > 1:
            return cls(*args)
        elif len(kwargs):
            return cls(**kwargs)
        else:
            return cls()
    
    @classmethod
    def android(cls, version: str = '10.2.0q'):
        return cls(1370, 51627, version, 'android', 'googleplay')
    
    @classmethod
    def ios(cls, version: str = '10.2.0q'):
        return cls(1370, 51679, version, 'ios', 'appstore')

    def __str__(self):
        return f'{self.game}:{self.client_p2}:{self.version}:{self.platform}:{self.store}'
    
    def urlencode(self):
        return urllib.parse.quote(str(self), safe = '')

class Downloader:
            chunk_size: int = 4194304
            response: requests.Response
            
            def __init__(
                self,
                response: requests.Response,
                file: PathOrBinaryFile,
                chunk_size: int = 4194304,
            ) -> None:
                self.response: requests.Response = response
                self._file = open_binary(file, 'w')
                self.file: BinaryIO | None = None
                self._iter: Generator | None = None
            
            def __enter__(self):
                self.file = self._file.__enter__()
                
                return self
            
            def __exit__(self, type, value, traceback):
                self._file.__exit__(type, value, traceback)
            
            def __len__(self):
                return int(self.response.headers.get('content-length', 0))
            
            def __iter__(self):
                self._iter = self.response.iter_content(chunk_size = self.chunk_size)
                return self
            
            def __next__(self):
                if self._iter is None:
                    raise StopIteration
                
                chunk = self._iter.__next__()
                self.file.write(chunk)
                return chunk
            
            def full_download(self, progress_bar = False) -> bytes:
                content = b''
                
                if progress_bar:
                    from rich.progress import Progress, Column, TextColumn, BarColumn, DownloadColumn, TimeRemainingColumn
                    from .console import console
                    
                    with Progress(
                        TextColumn("{task.description}", table_column = Column(ratio = 1)),
                        BarColumn(bar_width = None, table_column = Column(ratio = 2)),
                        DownloadColumn(table_column = Column(ratio = 1)),
                        TimeRemainingColumn(table_column = Column(ratio = 1)),
                        console = console,
                    ) as bar:
                        task = bar.add_task('Downloading...', total = len(self))
                        
                        for chunk in self:
                            content += chunk
                            bar.advance(task, len(chunk))
                else:
                    for chunk in self:
                        content += chunk
                
                return content

class Session(requests.Session):
    # headers: dict = {'Accept': '*/*'}
    
    MASTER_DOMAIN = furl('https://eve.gameloft.com')
    URL_DEFAULTS = {
        "pandora": "https://vgold.gameloft.com/",
        "status": "none",
    }
    SERVICE_DEFAULTS = {
        'asset': furl('https://bob-iris.gameloft.com'),
    }

    def __init__(
        self,
        client_id: ClientID,
        country: str = 'US',
    ):
        if not isinstance(client_id, ClientID):
            raise TypeError('client_id must be instance of ClientID')
        
        super().__init__()
        
        self.client_id = client_id
        
        self.services = {}
        self.country = country
        self._urls = None
        
        if self.client_id.platform == 'android':
            self.headers['User-Agent'] = 'connectivity_tracker/0.0 GlWebTools/2.0 AndroidOS/0.0 (AndroidDevice)'
    
    
    def send(self, *args, **kargs):
        response = super().send(*args, **kargs)

        def raise_for_status_wrapper(f: Callable):
            @wraps(f)
            def raise_for_status(*args, **kwargs):
                try:
                    f(*args, **kwargs)
                except requests.HTTPError as e:
                    e.add_note(response.text)
                    raise e
            
            return raise_for_status
        
        response.raise_for_status = raise_for_status_wrapper(response.raise_for_status)

        return response
    
    def download(
        self,
        url: str | furl,
        file: PathOrBinaryFile | None = None,
        chunk_size: int = 0x400000,
        params = None,
        data = None,
        headers = None,
        cookies = None,
        files = None,
        auth = None,
        timeout = None,
        allow_redirects = True,
        proxies = None,
        hooks = None,
        verify = None,
        cert = None,
        json = None,
    ):
        url = str(url)
        
        # Create the Request.
        req = requests.Request(
            method = 'GET',
            url = url,
            headers = headers,
            files = files,
            data = data or {},
            json = json,
            params = params or {},
            auth = auth,
            cookies = cookies,
            hooks = hooks,
        )
        prep = self.prepare_request(req)

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            url = prep.url,
            proxies = proxies,
            stream = True,
            verify = verify,
            cert = cert,
        )

        # Send the request.
        send_kwargs = {
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        send_kwargs.update(settings)
        response = self.send(prep, **send_kwargs)
        
        
        url = str(url)

        if file is None:
            file = io.BytesIO()
        
        return Downloader(
            response,
            file,
            chunk_size,
        )
    
    def get_service(self, service: str = 'auth'):
        if service in self.services:
            return self.services[service]
        
        try:
            self.services[service] = self._get_service(service)
        except requests.HTTPError:
            if service not in self.SERVICE_DEFAULTS:
                raise IndexError(f'Cannot find service "{service}"')
            
            return self.SERVICE_DEFAULTS[service]
        
        return self.services[service]

    def _get_service(self, service: str):
        url = furl(self.urls.get('pandora', self.URL_DEFAULTS['pandora']))
        url.path.set(str(self.client_id)).add('locate')
        
        url.query = {
            'service': service,
            'client_id': str(self.client_id),
        }
        
        response = requests.get(url)
        response.raise_for_status()
        return furl(scheme = 'https', host = response.text.split(':', 1)[0])
    
    def _get_datacenters(self, country: str = 'US') -> list[DataCenter]:
        url = self.MASTER_DOMAIN/'config'/str(self.client_id)/'datacenters'
        
        url.query = {
            'country': country,
        }
        
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def _get_datacenter(self, country: str = 'US') -> DataCenter:
        datacenters = self._get_datacenters(country = country)

        result: DataCenter = {}

        for datacenter in datacenters:
            if datacenter.get('status') != 'active':
                continue
            if result == {}:
                result = datacenter
            elif datacenter.get('preferred'):
                result = datacenter
        
        return result
    
    def _get_urls(self):
        datacenter = self._get_datacenter(self.country)
        
        datacenter.get('name')
        
        url = self.MASTER_DOMAIN/'config'/self.client_id.urlencode()/'datacenters'/datacenter.get('name', 'mdc')/'urls'
        
        response = requests.get(url)
        if response.status_code != 403:
            response.raise_for_status()
        result: dict[str, str] = response.json()

        return result
    
    @property
    def urls(self):
        if self._urls is None:
            self._urls = self._get_urls()
            if self._urls.get('status') != 'none':
                self._urls = self.URL_DEFAULTS.copy()
        
        return self._urls


class API:
    def __init__(
        self,
        client_id: ClientID | str | Literal['android', 'ios'],
        version: str | None = None,
        country: str = 'US',
    ) -> None:
        if client_id in ['android', 'ios']:
            if client_id == 'android':
                client_id = ClientID.android()
            else:
                client_id = ClientID.ios()
        else:
            client_id = ClientID.new(client_id)
        
        if version is not None:
            client_id.version = version
            
        self.session = Session(
            client_id,
            country = country,
        )
    
    @property
    def client_id(self):
        return self.session.client_id
    
    def get_dlc_manifest(self):
        url = self.session.get_service('asset')/'assets'/str(self.client_id)/'dlc_manifest'
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
        
    def get_astc_dlc_manifest(self):
        url = self.session.get_service('asset')/'assets'/str(self.client_id)/'astc_dlc_manifest'
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
        
    
    @overload
    def download_asset(
        self,
        asset: str,
        file: PathOrBinaryFile | None = None,
        stream: Literal[False] = False,
    ) -> bytes: ...
    @overload
    def download_asset(
        self,
        asset: str,
        file: PathOrBinaryFile | None = None,
        stream: Literal[True] = False,
    ) -> Downloader: ...
    def download_asset(
        self,
        asset: str,
        file: PathOrBinaryFile | None = None,
        stream: bool = False,
    ):
        url = self.session.get_service('asset')/'assets'/str(self.client_id)/asset
        
        if not stream:
            request = self.session.get(url)
            request.raise_for_status()
            if file is not None:
                with open_binary(file, 'w') as file_out:
                    file_out.write(request.content)
            return request.content
        
        request = self.session.download(url, file)
        request.response
        return request
