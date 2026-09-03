from pathlib import Path
from demoparser2 import DemoParser


DEMO_PATH = Path('data/raw/train_sources/demo/2026-09-01_19-31-10_17_de_inferno_team_Kay_vs_team_YY.dem')
PLAYER_NAME = ''


def main() -> None:
    parser = DemoParser(str(DEMO_PATH))
    print('=' * 60)
    print(f'Inspecting player: {PLAYER_NAME}')
    print('=' * 60)
    candidate_properties = ['team_name', 'team_num', 'health', 'armor_value', 'is_alive', 'X', 'Y', 'Z', 'yaw', 'pitch', 'active_weapon_name', 'player_slot']
    print('\n=== TICK PROPERTIES ===')
    available_properties = []

    for prop in candidate_properties:
        try:
            ticks = parser.parse_ticks([prop])
            matching = ticks[ticks['name'].astype(str).str.contains(PLAYER_NAME, case=False, na=False)]

            if not matching.empty:
                available_properties.append(prop)
                print(f'\n[{prop}]')
                print(matching[[column for column in ['tick', 'steamid', 'name', prop] if column in matching.columns]].drop_duplicates().head(20).to_string(index=False))
        except Exception as exc:
            print(f'{prop}: unavailable ({type(exc).__name__})')

    print('\n=== AVAILABLE PROPERTIES FOR PLAYER ===')
    print(available_properties)
    print('\n=== EVENTS ===')
    event_names = ['player_team', 'player_spawn', 'player_death', 'round_start', 'round_freeze_end', 'round_end', 'weapon_fire', 'player_hurt']

    for event_name in event_names:
        try:
            events = parser.parse_event(event_name)

            if events.empty:
                continue

            mask = events.astype(str).apply(lambda column: column.str.contains(PLAYER_NAME, case=False, na=False)).any(axis=1)
            matching = events[mask]

            if matching.empty:
                continue

            print(f'\n--- {event_name} ---')
            print(matching.head(20).to_string(index=False))
        except Exception as exc:
            print(f'{event_name}: unavailable ({type(exc).__name__})')

        print('\n=== ROUND TIMING ===')

    for event_name in ['round_start', 'round_freeze_end', 'round_end']:
        try:
            events = parser.parse_event(event_name)
            print(f'\n--- {event_name} ---')
            print(events.head(30).to_string(index=False))
        except Exception as exc:
            print(f'{event_name}: unavailable ({type(exc).__name__})')

if __name__ == '__main__':
    main()
