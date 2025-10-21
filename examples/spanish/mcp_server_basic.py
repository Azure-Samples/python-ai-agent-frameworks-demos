import random
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from faker import Faker
from mcp.server.fastmcp import FastMCP
from pydantic import Field

app = FastMCP()
fake = Faker()


@dataclass
class Hotel:
    name: str
    address: str
    location: str
    rating: float
    price_per_night: float
    hotel_type: str
    amenities: list[str]
    available_rooms: int


@dataclass
class HotelSuggestions:
    hotels: list[Hotel]


def validate_iso_date(date_str: str, param_name: str):
    """
    Valida que una cadena esté en formato ISO (YYYY-MM-DD) y devuelve la fecha parseada.

    Args:
        date_str: La cadena de fecha a validar
        param_name: Nombre del parámetro para mensajes de error

    Returns:
        El objeto de fecha parseado

    Raises:
        ValueError: Si la fecha no está en formato ISO o es inválida
    """
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not iso_pattern.match(date_str):
        raise ValueError(f"{param_name} debe estar en formato ISO (YYYY-MM-DD), se recibió: {date_str}")

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"{param_name} inválido: {e}")


@app.tool()
async def suggest_hotels(
    location: Annotated[str, Field(description="Ubicación (ciudad o área) para buscar hoteles")],
    check_in: Annotated[str, Field(description="Fecha de entrada en formato ISO (YYYY-MM-DD)")],
    check_out: Annotated[str, Field(description="Fecha de salida en formato ISO (YYYY-MM-DD)")],
) -> HotelSuggestions:
    """
    Sugiere hoteles basados en ubicación y fechas.
    """
    # Validar fechas
    check_in_date = validate_iso_date(check_in, "check_in")
    check_out_date = validate_iso_date(check_out, "check_out")

    # Asegurar que check_out sea después de check_in
    if check_out_date <= check_in_date:
        raise ValueError("La fecha de salida debe ser posterior a la fecha de entrada")

    # Crear datos simulados realistas para hoteles
    hotel_types = ["Lujo", "Boutique", "Económico", "Negocios"]
    amenities = ["WiFi gratis", "Piscina", "Spa", "Gimnasio", "Restaurante", "Bar", "Servicio a la habitación", "Estacionamiento"]

    # Generar una calificación entre 3.0 y 5.0
    def generate_rating():
        return round(random.uniform(3.0, 5.0), 1)

    # Generar un precio basado en el tipo de hotel
    def generate_price(hotel_type):
        price_ranges = {
            "Lujo": (250, 600),
            "Boutique": (180, 350),
            "Económico": (80, 150),
            "Resort": (200, 500),
            "Negocios": (150, 300),
        }
        min_price, max_price = price_ranges.get(hotel_type, (100, 300))
        return round(random.uniform(min_price, max_price))

    # Generar entre 3 y 8 hoteles
    num_hotels = random.randint(3, 8)
    hotels = []

    neighborhoods = [
        "Centro",
        "Distrito Histórico",
        "Zona Costera",
        "Distrito Financiero",
        "Barrio de las Artes",
        "Zona Universitaria",
    ]

    for i in range(num_hotels):
        hotel_type = random.choice(hotel_types)
        hotel_amenities = random.sample(amenities, random.randint(3, 6))
        neighborhood = random.choice(neighborhoods)

        hotel = Hotel(
            name=f"{hotel_type} {['Hotel', 'Inn', 'Suites', 'Resort', 'Plaza'][random.randint(0, 4)]}",
            address=fake.street_address(),
            location=f"{neighborhood}, {location}",
            rating=generate_rating(),
            price_per_night=generate_price(hotel_type),
            hotel_type=hotel_type,
            amenities=hotel_amenities,
            available_rooms=random.randint(1, 15),
        )
        hotels.append(hotel)

    # Ordenar por calificación para mostrar los mejores hoteles primero
    hotels.sort(key=lambda x: x.rating, reverse=True)
    return HotelSuggestions(hotels=hotels)


if __name__ == "__main__":
    app.run(transport="streamable-http")
