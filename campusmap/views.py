from dataclasses import dataclass

from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from campusmap.layout import floor_plan
from university.building import blocked_cells
from university.models import Room


@dataclass(frozen=True)
class RoomEntry:
    number: str
    url: str
    on_map: bool
    is_current: bool


@dataclass(frozen=True)
class FloorEntry:
    number: int
    url: str
    is_current: bool
    rooms: list[RoomEntry]


class MapView(TemplateView):
    template_name = "campusmap/map.html"
    http_method_names = ["get"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rooms = list(Room.objects.order_by("floor", "number"))
        floors = sorted({r.floor for r in rooms})
        code = self.kwargs.get("code")
        floor = self.kwargs.get("floor")
        current = None
        if code is not None:
            current = next((r for r in rooms if r.code == code), None)
            if current is None:
                raise Http404
            floor = current.floor
        elif floor is not None:
            if floor not in floors:
                raise Http404
        else:
            floor = floors[0] if floors else None
        plan = floor_plan(floor, rooms, current) if floor is not None else None
        floor_entries = [
            FloorEntry(
                f,
                reverse("campusmap:floor", args=[f]),
                f == floor,
                [
                    RoomEntry(
                        r.number,
                        reverse("campusmap:room", args=[r.code]),
                        bool(r.map_cell) and r.map_cell not in blocked_cells(f),
                        current is not None and r.pk == current.pk,
                    )
                    for r in rooms
                    if r.floor == f
                ],
            )
            for f in floors
        ]
        context["plan"] = plan
        context["floors"] = floor_entries
        context["current"] = current
        return context
