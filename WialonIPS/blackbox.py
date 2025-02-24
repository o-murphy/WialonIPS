import heapq
from dataclasses import dataclass, field
from fsm import Record
from datetime import datetime
import json

CACHE_FILE = "blackbox_heap.json"


@dataclass(order=True)
class PrioritizedRecord:
    priority: int
    timestamp: int
    record: Record = field(compare=False)  # Exclude `Record` from sorting


@dataclass
class BlackBox:
    timeout: int = 10
    queue: list = field(default_factory=list)

    def __post_init__(self):
        self._load_from_file()

    def on_record(self, r: Record):
        timestamp = int(datetime.now().timestamp())
        priority = -r.priority
        heapq.heappush(
            self.queue, PrioritizedRecord(priority, timestamp, r)
        )  # Negative priority for max-heap
        self._save_to_file()

    def peek(self, n=1):
        """Повертає кілька записів з найвищим пріоритетом стану, а потім часу."""
        if len(self.queue) >= n:
            # Повертає список з перших n записів
            return [self.queue[i].record for i in range(n)]
        return []
            
    def confirm(self, n=1):
        """Видаляє кілька записів після успішної відправки."""
        confirmed_records = []
        for _ in range(n):
            if self.queue:
                confirmed_records.append(heapq.heappop(self.queue))  # Видаляємо запис з найвищим пріоритетом
        self._save_to_file()
        return confirmed_records
        
    def _load_from_file(self):
        """Завантаження подій з файлу при старті."""
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                for item in data:
                    record = Record(**item['record'])  # Відновлюємо об'єкт Record
                    timestamp = int(item["timestamp"])  # Час зберігається в timestamp
                    priority = item["priority"]
                    heapq.heappush(self.queue, PrioritizedRecord(priority, timestamp, record))
        except (OSError, ValueError):
            pass  # Якщо файл відсутній або пошкоджений

    def _save_to_file(self):
        """Збереження черги в файл."""
        with open(CACHE_FILE, "w") as f:
            # Записуємо записи в черзі у файл
            json.dump([{
                "record": r.record.__dict__,
                "priority": r.priority,
                "timestamp": r.timestamp
            } for r in self.queue], f)

# Usage
# if __name__ == "__main__":
#     b = BlackBox()
#     b.observer.params["hi"] = IOElement(
#         priority=Priority.HIGH, operand=Operand.ON_CHANGE,
#         event_only=True,
#     )
#     b.observer.params["panic"] = IOElement(
#         priority=Priority.PANIC, operand=Operand.ON_CHANGE,
#         event_only=True,
#     )
#
#     b.observer.params["param1"] = IOElement(
#         value='5s',
#         priority=Priority.LOW, operand=Operand.ON_CHANGE,
#         event_only=False,
#     )
#
#     b.observer.params["battery"] = IOElement(
#         value=100.0,
#         priority=Priority.LOW, operand=Operand.ON_CHANGE,
#         event_only=False,
#     )
#
#
#     b.observer.upd_param("hi", 2)
#     b.observer.upd_param("panic", 1)
#     b.observer.upd_param("hi", 1)
#     print(b.peek()[0].full)
#     b.confirm()
#     print(b.peek()[0].full)
#     b.confirm()
#     print(b.peek()[0].full)
#     b.confirm()
#
#     from device import Device
#     d = Device()
#
#     print('C', d.coords[:-2])
#     b.observer.upd_positional(*d.coords[:-2])
#     b.observer.event()
#     full = b.peek()[0]
#     print(full)
#     print(full.full)
#     b.confirm()

# b'#D# 240225;190911.393702000;5027.282000;N;03031.428000;E;NA;NA;NA;NA;NA;NA;NA;NA;NA;param1:3:5s,battery:2:100.0;F771\r\n'
# b'#D# 240225;191951.926020000;5027.282000;N;03031.428000;E;NA;NA;NA;NA;NA;NA;NA;NA;NA;param1:3:5s,battery:2:100.0;