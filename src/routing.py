from pages.full_report import FullReportPage
from pages.home import HomePage
from pages.json_db_export import JsonDbExportPage
from pages.json_db_import import JsonDbImportPage
from pages.mixtures_prices import MixturesPricesPage
from pages.new_category import NewCategoryPage
from pages.new_plant_by_mixture import NewPlantByMixturePage
from pages.new_plant_by_npk import NewPlantByNPKPage

ROUTES = {
    'home': {'page': HomePage, 'takes_page_object': True},
    'category': {'page': NewCategoryPage, 'takes_page_object': True},
    'plant_by_npk': {'page': NewPlantByNPKPage, 'takes_page_object': True},
    'plant_by_mixture': {'page': NewPlantByMixturePage, 'takes_page_object': True},
    'mixtures_prices': {'page': MixturesPricesPage, 'takes_page_object': True},
    'general_report': {'page': FullReportPage, 'takes_page_object': True},
    'json_db_export': {'page': JsonDbExportPage, 'takes_page_object': True},
    'json_db_import': {'page': JsonDbImportPage, 'takes_page_object': True}
}
