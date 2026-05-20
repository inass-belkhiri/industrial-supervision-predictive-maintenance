import asyncio
import modbus_manager as modbus

async def test():
    await modbus.init_modbus()
    readings = await modbus.read_all_sensors({})
    for r in readings:
        print(f'Moule ({r.group_id},{r.mold_id}): {r.temperature}°C [{r.status}]')
    await modbus.close_modbus()

asyncio.run(test())