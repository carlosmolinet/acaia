import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from pyacaia_async.decode import Settings

SCAN_INTERVAL = timedelta(seconds=30)
UPDATE_DELAY = 15

_LOGGER = logging.getLogger(__name__)


class AcaiaApiCoordinator(DataUpdateCoordinator):
    """Class to handle fetching data from the La Marzocco API centrally"""

    def __init__(self, hass, config_entry, acaia_client):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Acaia API coordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=SCAN_INTERVAL
        )
        self._device_available = False
        self._battery_level = None

        self._acaia_client = acaia_client

    @property
    def acia_client(self):
        return self._acaia_client
    

    async def _async_update_data(self):
        try:
            scanner_count = bluetooth.async_scanner_count(self.hass, connectable=True)
            if scanner_count == 0:
                self.acia_client._connected = False
                _LOGGER.debug("Update coordinator: No bluetooth scanner available")
                return
            
            self._device_available = await bluetooth.async_address_present(
                    self.hass, 
                    self._acaia_client.mac, 
                    connectable=True
                )
            
            if not self._connected and self._device_available:
                _LOGGER.debug("Update coordinator: Connecting...")
                await self._acaia_client.connect(callback=self._on_data_received)

            elif not self._device_available:
                self.acia_client._connected = False
                _LOGGER.debug("Update coordinator: Device not available")

            else:
                await self._acaia_client.send_id()
        except Exception as ex:
            _LOGGER.error(ex)
            raise UpdateFailed("Error: %s", ex)
        
        return self._battery_level

    @callback
    def _on_data_received(self, characteristic, data):
        """ callback which gets called whenever the websocket receives data """
        if isinstance(data, Settings):
            self._battery_level = data.battery
        self.async_set_updated_data(self._battery_level)
