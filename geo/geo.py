from typing import Union, Dict, Optional, Iterable, List, Tuple
from collections import namedtuple
from cmath import isclose
import pandas as pd
import warnings
import requests
import geocoder
import re


class Geo(object):
    __slots__ = '__allowed_methods', '__rel_tol'
    __wkt_pattern: re.compile = re.compile(r'^POINT\((?P<x>\S+)\s+(?P<y>\S+)\)$')
    Point: namedtuple = namedtuple('Point', ('address', 'x', 'y'))  # mapping between address and coordinates

    def __init__(self, allowed_methods: Tuple[str] = ('arcgis', 'baidu', 'bing', 'gaode', 'geocodefarm', 'geolytica',
                                                      'geonames', 'ottawa', 'google', 'here', 'locationiq', 'mapbox',
                                                      'mapquest', 'opencage', 'osm', 'tamu', 'tomtom', 'w3w', 'yahoo',
                                                      'yandex', 'tgos'), rel_tol: float = 1e-09) -> None:
        """
        Configure 2 parameters 'allowed_methods' and 'tolerance',
        for basic usage don't pass any argument to the constructor.
        :param allowed_methods: tuple with all allowed methods.
                                Affected only on 'get_multiple_method_coordinates' method.
        :param rel_tol: is the relative tolerance – it is the maximum allowed difference between 'x' and 'y'
                        coordinates points of two sources 'wkt' and 'osm', relative to the larger absolute value
                        of 'a' or 'b'. For example, to set a tolerance of 5%, pass rel_tol=0.05.
                        The default tolerance is 1e-09, which assures that the two values are
                        the same within about 9 decimal digits. rel_tol must be greater than zero.
        """
        self.__allowed_methods: Tuple[str] = allowed_methods
        self.__rel_tol: float = rel_tol

    def __parse_wtk(self, in_str: str) -> Optional[Dict[str, str]]:
        """
        Parse input string using 'self.__wkt_pattern' and return dict with results.
        :param in_str: input string for parsing.
        :return: dict if parsing results is not null, else return 'None'
        """
        search_result = self.__wkt_pattern.search(in_str)
        result = search_result.groupdict() if search_result else None
        return result

    def __get_wkt(self, address: str, query_result) -> Optional[Point]:
        """
        Parse 'wkt' block and return processed data.
        :param address: single 'address' string.
        :param query_result: result of a work of any method from 'geocode' module.
        :return: 'Point' object.
        """
        result = None

        try:
            wkt = self.__parse_wtk(query_result.wkt) if query_result.wkt else None

        except AttributeError:
            pass

        else:
            if wkt:
                x, y = wkt.get('x', None), wkt.get('y', None)
                if x and y:
                    result = self.Point(address, float(x), float(y))

        return result

    def __get_osm(self, address: str, query_result) -> Optional[Point]:
        """
        Parse 'osm' block and return processed data.
        :param address: single 'address' string.
        :param query_result: result of a work of any method from 'geocode' module.
        :return: 'Point' object.
        """
        result = None

        try:
            osm = query_result.osm

        except AttributeError:
            pass

        else:
            if osm:
                x, y = osm.get('x', None), osm.get('y', None)
                if x and y:
                    result = self.Point(address, float(x), float(y))

        return result

    def __get_lat_and_lng(self, address: str, query_result) -> Optional[Point]:
        """
        Get two attributes ('wkt' and 'osm') from 'query_result', compare 'wkt.x' with 'osm.x', the same for 'y' and
        return any appropriated value. If values are different with given tolerance(self.__rel_tol), the ValueError
        will be raised.
        :param address: single 'address' string.
        :param query_result: result of a work of any method from 'geocode' module.
        :return: 'Point' object.
        """
        wkt = self.__get_wkt(address, query_result)
        osm = self.__get_osm(address, query_result)

        if wkt and osm:
            if isclose(wkt.x, osm.x, rel_tol=self.__rel_tol) and isclose(wkt.y, osm.y, rel_tol=self.__rel_tol):
                result = wkt

            else:
                raise ValueError(f'Values in the fields are not equal: WKT={wkt}\tOSM={osm}')

        else:
            result = (wkt or osm)

        return result

    def get_coordinates(self, address: Union[str, List[str]], method_name: str,
                        leave_null_values: bool = False) -> Optional[Union[Point, List[Point]]]:
        """
        Return coordinates Point('address', 'x', 'y') for each given address.
        :param address: single 'address' string or list of 'address' strings
        :param method_name: single 'method name' string.
        :param leave_null_values: if for any address from given sequence of addresses, coordinates didn't detected,
                                  it will be interpret as 'None' object. By default, that argument set to False and
                                  all such occurrences will be removed. To save 'None' values, set True.
        :return: return single 'Point' value or list of 'Point' objects.
        """
        result: list = []
        method = getattr(geocoder, method_name)

        with requests.Session() as session:
            if isinstance(address, str):
                try:
                    res = method(address, session=session)

                except Exception:
                    warnings.warn(f"Could not get any data via method '{method_name}'.", Warning)

                else:
                    result.append(self.__get_lat_and_lng(address, res))

            else:
                for addr in address:
                    try:
                        res = method(addr, session=session)

                    except Exception:
                        warnings.warn(f"Could not get any data via method '{method_name}'.", Warning)

                    else:
                        result.append(self.__get_lat_and_lng(addr, res))

        if not leave_null_values:
            result = list(filter(None, result))

        return result if len(result) > 1 else result[0] if result else None

    def get_multiple_method_coordinates(self, address: Union[str, List[str]],
                                        method_name_vec: Optional[Union[str, Iterable[str]]] = None) \
            -> Optional[pd.DataFrame]:
        """
        Return coordinates [x, y] for each address and for each given 'method'.
        :param address: single 'address' string or list of 'address' strings.
        :param method_name_vec: single 'method name' string or any iterable of 'method name' strings.
                                If not specified, will be used all methods from 'methods_confidence_map'.
        :return: concatenated DataFrame with indices from 'method_name_vec' and columns as 'address' values.
                 Also drop all rows that contains only null values.
        """
        result = None
        df_vec: list = []

        for method_name in method_name_vec if method_name_vec else self.__allowed_methods:
            if method_name not in self.__allowed_methods:
                warnings.warn(f'Method "{method_name}" not found in "methods_confidence_map".', Warning)

            else:
                current_res = self.get_coordinates(address, method_name, leave_null_values=True)

                if current_res:
                    data_: dict = {k: [[v.x, v.y] if v else None] for k, v in zip(address, current_res)}
                    df_vec.append(pd.DataFrame(data=data_, index=[method_name], columns=address))

        if df_vec:
            result: pd.DataFrame = pd.concat(df_vec)
            result.dropna(how='all', inplace=True)

        return result
