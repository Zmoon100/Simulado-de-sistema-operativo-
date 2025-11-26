import os
import time
from datetime import datetime
import random
from collections import deque

try:
    from rich.console import Console, Group  # type: ignore
    from rich.table import Table  # type: ignore
    from rich.panel import Panel  # type: ignore
    from rich.text import Text  # type: ignore
    from rich.align import Align  # type: ignore
    from rich import box  # type: ignore
except ImportError:
    Console = None
    Group = None
    Table = None
    Panel = None
    Text = None
    Align = None
    box = None

from .os_sim import OperatingSystem
from .process import ProcessState


class CommandLineInterface:
    def __init__(self, os_sim):
        self.os = os_sim
        self.rich_enabled = Console is not None and Table is not None and Panel is not None
        self.console = Console() if self.rich_enabled else None
        self.demo_mode = True
        self.demo_delay = 0.5
        self.palette = {
            'primary': 'cyan',
            'success': 'green',
            'warning': 'yellow',
            'danger': 'red',
            'muted': 'bright_black'
        }
        self.category_colors = {
            'PROCESO': 'cyan',
            'MEMORIA': 'blue',
            'CPU': 'magenta',
            'ARCHIVO': 'yellow',
            'E/S': 'yellow',
            'SEGURIDAD': 'red',
            'SISTEMA': 'white'
        }
        self.command_styles = {
            'ps': ('cyan', '🧠'),
            'create': ('green', '🌱'),
            'kill': ('red', '💥'),
            'schedule': ('magenta', '🌀'),
            'meminfo': ('blue', '📊'),
            'top': ('magenta', '📈'),
            'vmem': ('blue', '💾'),
            'ioinfo': ('yellow', '🔌'),
            'inode': ('green', '🗂'),
            'tlb_demo': ('blue', '📚'),
            'timeline': ('yellow', '⏱'),
            'history': ('cyan', '📜'),
            'ls': ('yellow', '📁'),
            'touch': ('yellow', '📝'),
            'cat': ('yellow', '📖'),
            'echo': ('yellow', '✏'),
            'rm': ('red', '🗑'),
            'demo': ('magenta', '🎬'),
            'help': ('white', '❓'),
            'clear': ('white', '🧽'),
            'exit': ('white', '🚪')
        }
        self.current_command = None
        self.current_command_color = self.palette['primary']
        self.stage_index = 0
        self.commands = {
            'help': self._help,
            'ps': self._list_processes,
            'create': self._create_process,
            'kill': self._kill_process,
            'schedrun': self._sched_run,
            'tickrate': self._tick_rate,
            'nuke': self._nuke,
            'meminfo': self._memory_info,
            'top': self._system_info,
            'vmem': self._virtual_memory_info,
            'tlb_demo': self._tlb_demo,
            'processflow': self._process_flow,
            'ioinfo': self._io_info,
            'schedpolicy': self._sched_policy,
            'dev': self._dev_command,
            'io': self._io_activate,
            'mkdir': self._mkdir,
            'cd': self._cd,
            'whereami': self._whereami,
            'touch': self._create_file,
            'cat': self._read_file,
            'echo': self._write_file,
            'rm': self._delete_file,
            'ls': self._list_files,
            'schedule': self._run_scheduler,
            'inode': self._inode_info,
            'timeline': self._timeline,
            'history': self._process_history,
            'login': self._login,
            'whoami': self._whoami,
            'security': self._security_status,
            'demo': self._demo_sequence,
            'clear': self._clear,
            'exit': self._exit
        }

    def _help(self, args):
        help_text = """
=== Simulador de Sistema Operativo ===

COMANDOS DISPONIBLES:

Procesos:
  ps                    - Lista todos los procesos
  create <nombre> [prioridad] [memoria] - Crea un nuevo proceso
  kill <pid>            - Termina un proceso
  nuke                  - Mata todos los procesos
  processflow <pid>     - Muestra ciclo de vida
  schedrun              - Ejecuta todos según política activa
  tickrate <kb>         - Ajusta velocidad (KB por tick)
  schedpolicy <RR|FIFO|SJF|PRIORITY> - Cambia política del planificador

Sistema:
  top                   - Muestra información del sistema
  meminfo               - Muestra información de memoria
  vmem                  - Estado de memoria virtual
  tlb_demo [cap] [pid:page ...] - Demo TLB LRU
  ioinfo                - Dispositivos e interrupciones
  timeline [n]          - Muestra últimos eventos
  history <pid>         - Historia detallada de un proceso
  clear                 - Limpia la pantalla

Archivos:
  touch <archivo>       - Crea un archivo vacío
  cat <archivo>         - Muestra el contenido de un archivo
  echo <texto> > <archivo> - Escribe texto en un archivo
  ls                    - Lista archivos
  rm <archivo>          - Elimina un archivo
  inode <ruta>          - Información i-nodo
  mkdir <directorio>    - Crea directorio
  cd <ruta>             - Cambia directorio
  cd ..                 - Regresa al directorio anterior
  whereami              - Muestra directorio actual
  
E/S:
  dev list              - Lista dispositivos de E/S
  dev on <disp>         - Activa dispositivo
  dev off <disp>        - Desactiva dispositivo
  dev mode <disp> <DMA|PROGRAMADO> - Cambia modo del dispositivo
  dev irq <disp> [nivel]- Genera una IRQ del dispositivo
  dev irq_demo          - Demostración visual de preempción por IRQ
  io <disp> [duración]  - Solicita E/S manual al dispositivo

Seguridad:
  login <usuario> <pass>- Autenticación
  whoami                - Usuario actual
  security              - Estado de seguridad
  demo                  - Corre la secuencia guiada
  help                  - Muestra esta ayuda
  exit                  - Sale del simulador
        """
        if not self.rich_enabled:
            return help_text
        sections = {
            "Procesos": [
                "`ps` - Lista todos los procesos",
                "`create <nombre> [prioridad] [memoria]` - Crea un proceso",
                "`kill <pid>` - Termina un proceso",
                "`nuke` - Mata todos los procesos",
                "`processflow <pid>` - Ciclo de vida",
                "`schedrun` - Ejecuta según política",
                "`tickrate <kb>` - Velocidad por tick",
                "`schedpolicy <RR|FIFO|SJF|PRIORITY>` - Cambia política"
            ],
            "Sistema": [
                "`top` - Información general",
                "`meminfo` - Estado de memoria",
                "`vmem` - Memoria virtual",
                "`tlb_demo [cap] [pid:page ...]` - Demo TLB LRU",
                "`ioinfo` - Dispositivos E/S",
                "`timeline [n]` - Últimos eventos",
                "`history <pid>` - Historia de un proceso",
                "`clear` - Limpia la pantalla"
            ],
            "Archivos": [
                "`touch <archivo>` - Crea archivo",
                "`cat <archivo>` - Lee archivo",
                "`echo <texto> > <archivo>` - Escribe archivo",
                "`ls` - Lista archivos",
                "`rm <archivo>` - Elimina archivo",
                "`inode <ruta>` - Información i-nodo",
                "`mkdir <directorio>` - Crea directorio",
                "`cd <ruta>` - Cambia directorio",
                "`cd ..` - Regresa al directorio anterior",
                "`whereami` - Muestra directorio actual"
            ],
            "E/S": [
                "`dev list` - Lista dispositivos",
                "`dev on <dispositivo>` - Activa dispositivo",
                "`dev off <dispositivo>` - Desactiva dispositivo",
                "`dev mode <dispositivo> <DMA|PROGRAMADO>` - Cambia modo",
                "`dev irq <dispositivo> [nivel]` - Genera IRQ",
                "`dev irq_demo` - Demo de preempción por IRQ",
                "`io <dispositivo> [duración]` - Solicitud E/S"
            ],
            "Otros": [
                "`login <user> <pass>` - Autenticación",
                "`whoami` - Usuario activo",
                "`security` - Seguridad",
                "`demo` - Secuencia guiada",
                "`help` - Ayuda",
                "`exit` - Salir"
            ]
        }
        grid = Table.grid(padding=1)
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        for title, commands in sections.items():
            command_list = "\n".join(commands)
            grid.add_row(f"[bold]{title}[/]", command_list)
        return Panel(
            grid,
            title="Guía de Comandos",
            border_style=self.palette['primary'],
            box=box.ROUNDED if box else None
        )

    def _list_processes(self, args):
        processes = self.os.cpu_scheduler.get_all_processes()
        if not processes:
            if self.rich_enabled:
                return Panel("No hay procesos en el sistema", title="Procesos", style="yellow")
            return "No hay procesos en el sistema"
        running = self.os.cpu_scheduler.get_running_process()
        if not self.rich_enabled:
            output = "\n=== PROCESOS ===\n"
            output += f"{'PID':<6} {'Nombre':<15} {'Estado':<12} {'Prioridad':<10} {'Memoria':<10} {'CPU Time':<10}\n"
            output += "-" * 70 + "\n"
            for p in processes:
                output += f"{p.pid:<6} {p.name:<15} {p.state.value:<12} {p.priority:<10} {p.memory_size:<10} {p.cpu_time:<10}\n"
            if running:
                output += f"\nProceso en ejecución: PID {running.pid} - {running.name}\n"
            return output
        table = Table(
            title="Procesos activos",
            show_lines=True,
            header_style="bold cyan",
            box=box.SIMPLE_HEAVY if box else None
        )
        table.add_column("PID", justify="right", style="bold white")
        table.add_column("Nombre", style="bold")
        table.add_column("Estado", style="magenta")
        table.add_column("Prioridad", justify="center")
        table.add_column("Memoria", justify="right")
        table.add_column("CPU Time", justify="right")
        state_colors = {
            ProcessState.NEW: "bright_black",
            ProcessState.READY: "green",
            ProcessState.RUNNING: "cyan",
            ProcessState.WAITING: "yellow",
            ProcessState.TERMINATED: "red"
        }
        for p in processes:
            table.add_row(
                str(p.pid),
                p.name,
                f"[{state_colors.get(p.state, 'white')}]" + p.state.value + "[/]",
                str(p.priority),
                f"{p.memory_size} KB",
                f"{p.cpu_time}"
            )
        self._print(table)
        if running:
            return Panel(
                f"PID {running.pid} • {running.name}\nPrioridad: {running.priority}\nCPU Time: {running.cpu_time}",
                title="Proceso en ejecución",
                title_align="left",
                style="bold green",
                box=box.ROUNDED if box else None
            )
        return None

    def _create_process(self, args):
        if not args:
            return "Uso: create <nombre> [prioridad] [memoria]"
        name = args[0]
        priority = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
        memory = int(args[2]) if len(args) > 2 and args[2].isdigit() else 100
        process, message = self.os.create_process(name, priority, memory)
        success = process is not None
        extra = ""
        if success:
            detail = f"PID: {process.pid} • Prioridad: {process.priority} • Memoria: {process.memory_size} KB"
            extra = f"\n{detail}" if self.rich_enabled else f" ({detail})"
        return self._styled_feedback(message + extra, success)

    def _kill_process(self, args):
        if not args or not args[0].isdigit():
            return "Uso: kill <pid>"
        pid = int(args[0])
        success, message = self.os.kill_process(pid)
        return self._styled_feedback(message, success)

    def _nuke(self, args):
        processes = list(self.os.cpu_scheduler.get_all_processes())
        if not processes:
            return self._styled_feedback("No hay procesos activos", success=False, title="Nuke")
        count = 0
        for p in processes:
            ok, _ = self.os.kill_process(p.pid)
            if ok:
                count += 1
        msg = f"Terminados {count} procesos activos"
        self.os.log_event("PROCESO", msg)
        return self._styled_feedback(msg, success=True, title="Nuke")

    def _memory_info(self, args):
        info = self.os.memory_manager.get_memory_info()
        if not self.rich_enabled:
            output = "\n=== INFORMACIÓN DE MEMORIA ===\n"
            output += f"Memoria Total:     {info['total']} KB\n"
            output += f"Memoria Usada:     {info['used']} KB\n"
            output += f"Memoria Disponible: {info['available']} KB\n"
            output += f"Uso:               {info['usage_percent']:.2f}%\n"
            return output
        usage_bar = self._build_usage_bar(info['usage_percent'])
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_row("Memoria total", f"{info['total']} KB")
        table.add_row("Memoria usada", f"{info['used']} KB")
        table.add_row("Memoria disponible", f"{info['available']} KB")
        table.add_row("Uso", f"{info['usage_percent']:.2f}%")
        table.add_row(" ", usage_bar)
        return Panel(table, title="Memoria", border_style="blue", box=box.ROUNDED if box else None)

    def _system_info(self, args):
        info = self.os.get_system_info()
        if not self.rich_enabled:
            output = "\n=== INFORMACIÓN DEL SISTEMA ===\n"
            output += f"Tiempo activo:     {info['uptime']}\n"
            output += f"Procesos totales:  {info['total_processes']}\n"
            output += f"Procesos listos:   {info['ready_processes']}\n"
            output += f"Memoria usada:     {info['memory']['usage_percent']:.2f}%\n"
            if info['running_process']:
                p = info['running_process']
                output += f"\nProceso en ejecución:\n"
                output += f"  PID: {p.pid}\n"
                output += f"  Nombre: {p.name}\n"
                output += f"  Prioridad: {p.priority}\n"
                output += f"  Tiempo CPU: {p.cpu_time}\n"
            return output
        grid = Table.grid(padding=(0, 1))
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        grid.add_row("Tiempo activo", info['uptime'])
        grid.add_row("Procesos totales", str(info['total_processes']))
        grid.add_row("Procesos listos", str(info['ready_processes']))
        grid.add_row("Uso de memoria", f"{info['memory']['usage_percent']:.2f}% {self._build_usage_bar(info['memory']['usage_percent'])}")
        panels = [Panel(grid, title="Sistema", border_style="cyan", box=box.ROUNDED if box else None)]
        if info['running_process']:
            p = info['running_process']
            detail = Table.grid(padding=0)
            detail.add_column(justify="left")
            detail.add_row(f"PID: {p.pid}")
            detail.add_row(f"Nombre: {p.name}")
            detail.add_row(f"Prioridad: {p.priority}")
            detail.add_row(f"Tiempo CPU: {p.cpu_time}")
            panels.append(Panel(detail, title="Proceso en ejecución", border_style="green", box=box.ROUNDED if box else None))
        return Group(*panels)

    def _virtual_memory_info(self, args):
        status = self.os.virtual_memory.get_status()
        accesses = self.os.virtual_memory.access_log[-5:]
        if not self.rich_enabled:
            lines = [
                "=== MEMORIA VIRTUAL ===",
                f"Tamaño de página: {status['page_size']} KB",
                f"Marcos usados/libres: {status['frames_used']}/{status['frames_total']}",
                f"Fallos de página: {status['page_faults']}",
                "Últimos accesos:"
            ]
            for pid, page, fault in accesses:
                lines.append(f"PID {pid} página {page} {'FAULT' if fault else 'OK'}")
            return "\n".join(lines)
        table = Table(title="Memoria Virtual", box=box.ROUNDED if box else None)
        table.add_column("Dato", justify="left", style="bold")
        table.add_column("Valor", justify="right")
        table.add_row("Tamaño página", f"{status['page_size']} KB")
        table.add_row("Marcos usados", str(status['frames_used']))
        table.add_row("Marcos libres", str(status['frames_free']))
        table.add_row("Fallos de página", str(status['page_faults']))
        log_table = Table(title="Accesos recientes", box=box.SIMPLE if box else None)
        log_table.add_column("PID")
        log_table.add_column("Página")
        log_table.add_column("Evento")
        for pid, page, fault in accesses:
            log_table.add_row(str(pid), str(page), "FAULT" if fault else "HIT")
        return Group(table, log_table)

    def _tlb_demo(self, args):
        capacity = None
        tokens = []
        if args:
            if args[0].isdigit():
                capacity = int(args[0])
                tokens = args[1:]
            else:
                tokens = args
        if capacity:
            self.os.virtual_memory.set_tlb_capacity(capacity)
        # reiniciar TLB para que la demo muestre hits/misses consistentes
        self.os.virtual_memory.reset_tlb()
        seq = []
        for t in tokens:
            if ':' in t:
                a, b = t.split(':', 1)
                if a.isdigit() and b.isdigit():
                    seq.append((int(a), int(b)))
        if not seq:
            # secuencia por defecto con HITS claros y alguna evicción
            seq = [
                (1,0),(2,1),(3,2),    # misses iniciales
                (1,0),(2,1),(3,2),    # hits sobre las mismas entradas
                (4,0),                # miss agrega nueva entrada
                (5,1),                # miss provoca evicción LRU
                (1,0),                # puede ser miss si fue evictado
            ]
        events = []
        for pid, page in seq:
            hit, msg = self.os.virtual_memory.tlb_access(pid, page)
            self.os.log_event("MEMORIA", msg)
            events.append((pid, page, hit, msg))
        status = self.os.virtual_memory.get_tlb_status()
        if not self.rich_enabled:
            lines = [
                "=== TLB DEMO (LRU) ===",
                f"Capacidad: {status['capacity']}",
                f"Entradas: {status['size']}",
                f"HITS/MISSES: {status['hits']}/{status['misses']}",
                "Orden (LRU→MRU):",
                ", ".join([f"pid={p} page={pg}" for (p, pg) in status['order']]),
                "Eventos:"
            ]
            for pid, page, hit, msg in events:
                lines.append(f"pid={pid} page={page} {'HIT' if hit else 'MISS'}: {msg}")
            return "\n".join(lines)
        table = Table(title="TLB Estado", box=box.ROUNDED if box else None)
        table.add_column("Dato")
        table.add_column("Valor")
        table.add_row("Capacidad", str(status['capacity']))
        table.add_row("Entradas", str(status['size']))
        table.add_row("HITS", str(status['hits']))
        table.add_row("MISSES", str(status['misses']))
        order = Table(title="Orden LRU→MRU", box=box.SIMPLE if box else None)
        order.add_column("Pos")
        order.add_column("PID")
        order.add_column("Página")
        for idx, (p, pg) in enumerate(status['order']):
            order.add_row(str(idx+1), str(p), str(pg))
        log = Table(title="Eventos", box=box.SIMPLE if box else None)
        log.add_column("PID")
        log.add_column("Página")
        log.add_column("Tipo")
        log.add_column("Detalle")
        for pid, page, hit, msg in events:
            log.add_row(str(pid), str(page), "HIT" if hit else "MISS", msg)
        return Group(table, order, log)

    def _process_flow(self, args):
        if not args or not args[0].isdigit():
            return "Uso: processflow <pid>"
        pid = int(args[0])
        flow = self.os.get_process_flow(pid)
        if flow is None:
            return self._styled_feedback("Proceso no encontrado", success=False, title="Ciclo de vida")
        if not flow:
            return self._styled_feedback("Sin transiciones registradas aún", success=False, title="Ciclo de vida")
        if not self.rich_enabled:
            chain = " -> ".join([entry['state'] for entry in flow])
            return f"PID {pid}: {chain}"
        timeline = Table(title=f"Ciclo PID {pid}", box=box.ROUNDED if box else None)
        timeline.add_column("Tiempo")
        timeline.add_column("Estado")
        timeline.add_column("Nota")
        for entry in flow:
            timeline.add_row(
                entry['time'].strftime("%H:%M:%S"),
                entry['state'],
                entry['note'] or "-"
            )
        return timeline

    def _io_info(self, args):
        status = self.os.io_manager.get_status()
        if not self.rich_enabled:
            lines = ["=== DISPOSITIVOS E/S ==="]
            for dev in status:
                lines.append(f"{dev['name']} - {dev['mode']} - {'BUSY' if dev['busy'] else 'Libre'}")
            return "\n".join(lines)
        table = Table(title="Dispositivos", box=box.ROUNDED if box else None)
        table.add_column("Dispositivo", style="bold")
        table.add_column("Modo")
        table.add_column("Estado")
        table.add_column("Última solicitud")
        for dev in status:
            last = dev['last_request']
            detail = "-"
            if last:
                detail = f"PID {last['pid']} ({last['duration']}u) {last['timestamp'].strftime('%H:%M:%S')}"
            table.add_row(
                dev['name'],
                dev['mode'],
                "BUSY" if dev['busy'] else "Libre",
                detail
            )
        return table

    def _inode_info(self, args):
        target = None
        if args and args[0]:
            raw = args[0]
            target = raw if raw.startswith('/') else f"{self.os.file_system.get_cwd().rstrip('/')}/{raw}"
        else:
            target = self.os.file_system.get_cwd()
        info = self.os.file_system.get_file_info(target)
        is_file = info is not None
        if not is_file:
            info = self.os.file_system.get_path_info(target)
        if not info:
            return self._styled_feedback("Ruta no encontrada", success=False, title="Inode")
        if is_file:
            size_bytes = len(self.os.file_system.files[target].content.encode())
            entry = {
                'path': info['path'],
                'type': 'file',
                'size': f"{size_bytes} B",
                'owner': info['owner'],
                'group': info['group'],
                'perms': info['perms'],
                'hash': info['hash'],
                'created_at': info['created_at'],
                'accessed_at': info['accessed_at'],
                'modified_at': info['modified_at']
            }
        else:
            children = self.os.file_system.directories.get(target, [])
            entry = {
                'path': info['path'],
                'type': 'dir',
                'size': f"{len(children)} items",
                'owner': info['owner'],
                'group': info['group'],
                'perms': info['perms'],
                'hash': info['hash'],
                'created_at': info['created_at'],
                'accessed_at': info['accessed_at'],
                'modified_at': info['modified_at']
            }
        if not self.rich_enabled:
            lines = ["=== INODE INFO ==="]
            lines.append(f"{entry['path']} [{entry['type']}] {entry['size']} {entry['perms']} {entry['owner']}:{entry['group']}")
            lines.append(f"creación: {entry['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"último acceso: {entry['accessed_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"última modificación: {entry['modified_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            return "\n".join(lines)
        table = Table(title="i-nodo", box=box.SIMPLE_HEAVY if box else None)
        table.add_column("Campo", style="bold")
        table.add_column("Valor")
        rows = [
            ("Ruta", entry['path']),
            ("Tipo", entry['type']),
            ("Tamaño", entry['size']),
            ("Propietario", entry['owner']),
            ("Grupo", entry['group']),
            ("Permisos", entry['perms']),
            ("Hash", entry['hash'][:12] + "..." if entry['hash'] else "-"),
            ("Creación", entry['created_at'].strftime('%Y-%m-%d %H:%M:%S')),
            ("Último acceso", entry['accessed_at'].strftime('%Y-%m-%d %H:%M:%S')),
            ("Última modificación", entry['modified_at'].strftime('%Y-%m-%d %H:%M:%S'))
        ]
        for k, v in rows:
            table.add_row(k, v)
        return table

    def _timeline(self, args):
        limit = None
        if args and args[0].isdigit():
            limit = int(args[0])
        events = self.os.get_timeline(limit)
        if not events:
            return self._styled_feedback("Aún no hay eventos registrados", success=False, title="Timeline")
        if not self.rich_enabled:
            lines = ["=== TIMELINE ==="]
            for e in events:
                timestamp = e['timestamp'].strftime("%H:%M:%S")
                lines.append(f"[{e['step']}] {timestamp} {e['category']}: {e['message']}")
            return "\n".join(lines)
        table = Table(
            title="Línea de tiempo",
            box=box.SIMPLE_HEAVY if box else None,
            header_style="bold white",
            row_styles=["dim", "none"]
        )
        table.add_column("#", justify="right")
        table.add_column("Hora")
        table.add_column("Tipo")
        table.add_column("Detalle")
        for e in events:
            color = self.category_colors.get(e['category'], 'white')
            timestamp = e['timestamp'].strftime("%H:%M:%S")
            detail = e['message']
            if e['pid']:
                detail += f" [PID {e['pid']}]"
            table.add_row(
                str(e['step']),
                timestamp,
                f"[{color}]" + e['category'] + "[/]",
                detail
            )
        return table

    def _process_history(self, args):
        if not args or not args[0].isdigit():
            return "Uso: history <pid>"
        pid = int(args[0])
        history = self.os.get_process_history(pid)
        if history is None:
            return self._styled_feedback(f"No se encontró el proceso {pid}", success=False, title="Historial")
        if not history:
            return self._styled_feedback(f"El proceso {pid} no tiene eventos registrados aún", success=False, title="Historial")
        if not self.rich_enabled:
            lines = [f"=== HISTORIAL PID {pid} ==="]
            for e in history:
                timestamp = e['timestamp'].strftime("%H:%M:%S")
                lines.append(f"[{e['step']}] {timestamp} {e['category']}: {e['message']}")
            return "\n".join(lines)
        table = Table(
            title=f"Historia del proceso {pid}",
            box=box.ROUNDED if box else None,
            row_styles=["dim", "none"]
        )
        table.add_column("#", justify="right")
        table.add_column("Hora")
        table.add_column("Evento")
        for e in history:
            timestamp = e['timestamp'].strftime("%H:%M:%S")
            color = self.category_colors.get(e['category'], 'white')
            table.add_row(
                str(e['step']),
                timestamp,
                f"[{color}]" + e['message'] + "[/]"
            )
        return table

    def _demo_sequence(self, args):
        try:
            self.os.file_system.delete_file("demo_log.txt")
        except Exception:
            pass
        self._print(self._styled_feedback("Autenticando", success=True, title="Demo"))
        self._print(self._login(["root", "root"]))
        self._print(self._whoami([]))

        def run_policy_block(policy_name):
            self._print(self._styled_feedback(f"Política: {policy_name}", success=True, title="Planificador"))
            self._print(self._sched_policy([policy_name]))
            names = [f"{policy_name.lower()}_{i}" for i in range(1, 6)]
            for name in names:
                prio = random.randint(1, 10)
                avail = getattr(self.os.memory_manager, 'available_memory', 1024)
                mem = random.choice([60, 80, 100, 120, 140])
                if mem > avail:
                    mem = max(20, min(avail - 20, mem))
                if mem <= 0 or mem > avail:
                    continue
                res = self._create_process([name, str(prio), str(mem)])
                if res is not None:
                    self._print(res)
            self._print(self._tick_rate(["20"]))
            self._print(self._sched_run([]))

        run_policy_block("RR")
        run_policy_block("FIFO")
        run_policy_block("SJF")
        run_policy_block("PRIORITY")

        self._print(self._styled_feedback("Demostración de IRQ", success=True, title="IRQ"))
        self._print(self._dev_command(["irq_demo"]))
        self._print(self._io_info([]))
        self._print(self._mkdir(["docs"]))
        self._print(self._cd(["docs"]))
        self._print(self._whereami([]))
        self._print(self._create_file(["readme.txt"]))
        self._print(self._list_files([]))
        self._print(self._cd([".."]))
        self._print(self._create_file(["demo_log.txt"]))
        self._print(self._write_file(["Sistema", "en", "demo", ">", "demo_log.txt"]))
        self._print(self._read_file(["demo_log.txt"]))
        self._print(self._inode_info([]))
        self._print(self._timeline(["64"]))
        if self.rich_enabled:
            self._print(self._styled_feedback(f"Planificador: {self.os.cpu_scheduler.policy}", success=True, title="Estado Planificador"))
        nuke_result = self._nuke([])
        if nuke_result is not None:
            self._print(nuke_result)
        return self._styled_feedback("Demo completada. Usa 'timeline' o 'history' para seguir explorando.", success=True, title="Demo")

    def _resolve_demo_args(self, raw_args, context):
        resolved = []
        for arg in raw_args:
            if arg.startswith("{") and arg.endswith("}"):
                key = arg[1:-1]
                value = context.get(key)
                resolved.append(str(value) if value is not None else key)
            else:
                resolved.append(arg)
        return resolved

    def _get_pid_by_name(self, name):
        processes = self.os.cpu_scheduler.get_all_processes()
        matches = [p for p in processes if p.name == name]
        if not matches:
            return None
        matches.sort(key=lambda p: p.created_at, reverse=True)
        return matches[0].pid

    def _create_file(self, args):
        if not args:
            return "Uso: touch <archivo>"
        success, message = self.os.file_system.create_file(args[0])
        if success:
            self.os.log_event("ARCHIVO", f"Creado archivo '{args[0]}'")
        return self._styled_feedback(message, success)

    def _mkdir(self, args):
        if not args:
            return "Uso: mkdir <directorio>"
        success, message = self.os.file_system.create_directory(args[0])
        if success:
            self.os.log_event("ARCHIVO", f"Creado directorio '{args[0]}'")
        return self._styled_feedback(message, success)

    def _cd(self, args):
        if not args:
            return "Uso: cd <ruta>"
        success, info = self.os.file_system.change_directory(args[0])
        if success:
            self.os.log_event("ARCHIVO", f"Directorio actual: {info}")
        return self._styled_feedback(info if success else info, success)

    def _whereami(self, args):
        cwd = self.os.file_system.get_cwd()
        return cwd

    def _read_file(self, args):
        if not args:
            return "Uso: cat <archivo>"
        content, error = self.os.file_system.read_file(args[0])
        if error:
            return self._styled_feedback(error, success=False)
        self.os.log_event("ARCHIVO", f"Leído archivo '{args[0]}'")
        integrity_note = ""
        if self.os.security_manager:
            key = f"file_{self.os.file_system._get_full_path(args[0])}"
            ok, msg = self.os.security_manager.verify_integrity(key, content or "")
            integrity_note = f"\nIntegridad: {msg}"
        if self.rich_enabled:
            body = content if content else "[bright_black](archivo vacío)"
            return Panel(body, title=f"Archivo: {args[0]}", border_style=self.palette['primary'], box=box.ROUNDED if box else None)
        return (content if content else "(archivo vacío)") + integrity_note

    def _write_file(self, args):
        if len(args) < 3 or args[-2] != '>':
            return "Uso: echo <texto> > <archivo>"
        text = ' '.join(args[:-2])
        filename = args[-1]
        success, message = self.os.file_system.write_file(filename, text)
        if success:
            self.os.log_event("ARCHIVO", f"Actualizado archivo '{filename}'", metadata={'longitud': len(text)})
        return self._styled_feedback(message, success)

    def _delete_file(self, args):
        if not args:
            return "Uso: rm <archivo>"
        success, message = self.os.file_system.delete_file(args[0])
        if success:
            self.os.log_event("ARCHIVO", f"Eliminado archivo '{args[0]}'")
        return self._styled_feedback(message, success)

    def _login(self, args):
        if len(args) < 2:
            return "Uso: login <usuario> <password>"
        success, message = self.os.security_manager.authenticate(args[0], args[1])
        self.os.log_event("SEGURIDAD", f"Login de {args[0]}: {'OK' if success else 'Fallo'}")
        return self._styled_feedback(message, success, title="Login")

    def _whoami(self, args):
        user = self.os.security_manager.current_user
        group = self.os.security_manager.get_user_group(user)
        return f"{user} ({group})"

    def _security_status(self, args):
        sec = self.os.security_manager
        users = sec.list_users()
        registry = sec.integrity_registry
        if not self.rich_enabled:
            lines = [f"Usuario actual: {sec.current_user}"]
            lines.append("Usuarios:")
            for u in users:
                lines.append(f" - {u['user']} ({u['group']})")
            lines.append(f"Hashes registrados: {len(registry)}")
            return "\n".join(lines)
        user_table = Table(title="Usuarios", box=box.ROUNDED if box else None)
        user_table.add_column("Usuario")
        user_table.add_column("Grupo")
        for u in users:
            user_table.add_row(u['user'], u['group'])
        hash_table = Table(title="Integridad registrada", box=box.SIMPLE if box else None)
        hash_table.add_column("Clave")
        hash_table.add_column("Hash")
        if registry:
            for key, value in registry.items():
                hash_table.add_row(key, value[:16] + "...")
        else:
            hash_table.add_row("-", "Sin registros")
        header = Panel.fit(
            f"[bold]{sec.current_user}[/] conectado",
            border_style=self.palette['primary'],
            box=box.ROUNDED if box else None
        )
        return Group(header, user_table, hash_table)

    def _list_files(self, args):
        entries = getattr(self.os.file_system, 'list_directory', None)
        files = entries() if entries else self.os.file_system.list_files()
        if not files:
            return self._styled_feedback("No hay archivos", success=False, title="Archivos")
        if not self.rich_enabled:
            return "\n".join(files)
        table = Table(title="Archivos en el directorio actual", box=box.SIMPLE_HEAVY if box else None)
        table.add_column("Ruta", style="bold white")
        table.add_column("Permisos")
        table.add_column("Owner")
        for path in files:
            info = getattr(self.os.file_system, 'get_path_info', None)
            data = info(path) if info else (self.os.file_system.get_file_info(path) or {})
            table.add_row(path, data.get('perms', 'dir' if path in getattr(self.os.file_system, 'directories', {}) else '---'), data.get('owner', '?'))
        return table

    def _run_scheduler(self, args):
        process = self.os.run_scheduler_cycle()
        if not process:
            if self.rich_enabled:
                return Panel("No hay procesos para planificar", title="Planificador", style="yellow")
            return "No hay procesos para planificar"
        self.os.log_event("CPU", f"Quantum asignado a PID {process.pid}", process=process, metadata={'cpu_time': process.cpu_time})
        if not self.rich_enabled:
            return f"Planificando proceso: PID {process.pid} - {process.name} (Tiempo CPU: {process.cpu_time})"
        bar = self._build_usage_bar(min(process.cpu_time, 100), width=20, color="cyan")
        return Panel(
            f"PID {process.pid} - {process.name}\nPrioridad: {process.priority}\nCPU acumulado: {process.cpu_time}\n{bar}",
            title="Planificador",
            border_style="magenta",
            box=box.ROUNDED if box else None
        )

    def _sched_policy(self, args):
        if not args:
            return "Uso: schedpolicy <RR|FIFO|SJF|PRIORITY>"
        ok = self.os.cpu_scheduler.set_policy(args[0].upper())
        if not ok:
            return self._styled_feedback("Política no reconocida", success=False, title="Planificador")
        return self._styled_feedback(f"Política cambiada a {self.os.cpu_scheduler.policy}", success=True, title="Planificador")

    def _tick_rate(self, args):
        if not args or not args[0].isdigit():
            return "Uso: tickrate <kb>"
        value = int(args[0])
        self.os.tick_kb = max(1, value)
        return self._styled_feedback(f"Tickrate ajustado a {self.os.tick_kb} KB/tick", success=True, title="Planificador")

    def _sched_run(self, args):
        processes = [p for p in self.os.cpu_scheduler.get_all_processes() if getattr(p, 'remaining_kb', p.memory_size) > 0]
        if not processes:
            return self._styled_feedback("No hay procesos para ejecutar", success=False, title="Planificador")
        tick = self.os.tick_kb
        policy = self.os.cpu_scheduler.policy
        tick_counter = 1
        def apply_tick(proc):
            left = getattr(proc, 'remaining_kb', proc.memory_size)
            if left <= 0:
                return True
            new_left = max(0, left - tick)
            setattr(proc, 'remaining_kb', new_left)
            proc.cpu_time += 1
            total = proc.memory_size
            done = total - new_left
            percent = int((done / total) * 100)
            if new_left == 0:
                self._print(f"tick {tick_counter}, proceso {proc.name} terminado")
                self.os.kill_process(proc.pid)
                return True
            else:
                self._print(f"tick {tick_counter}, proceso {proc.name} {percent}% completado")
                return False
        if policy == "RR":
            dq = deque(processes)
            while dq:
                proc = dq.popleft()
                finished = apply_tick(proc)
                tick_counter += 1
                if not finished:
                    dq.append(proc)
        elif policy == "FIFO":
            for proc in processes:
                while getattr(proc, 'remaining_kb', 0) > 0:
                    finished = apply_tick(proc)
                    tick_counter += 1
                    if finished:
                        break
        elif policy == "SJF":
            ordered = sorted(processes, key=lambda p: getattr(p, 'remaining_kb', p.memory_size))
            for proc in ordered:
                while getattr(proc, 'remaining_kb', 0) > 0:
                    finished = apply_tick(proc)
                    tick_counter += 1
                    if finished:
                        break
        elif policy == "PRIORITY":
            ordered = sorted(processes, key=lambda p: p.priority)
            for proc in ordered:
                while getattr(proc, 'remaining_kb', 0) > 0:
                    finished = apply_tick(proc)
                    tick_counter += 1
                    if finished:
                        break
        return self._styled_feedback("Ejecución completada", success=True, title="Planificador")

    def _dev_command(self, args):
        if not args:
            return "Uso: dev <list|on|off|mode> [args]"
        sub = args[0].lower()
        if sub == "list":
            status = self.os.io_manager.get_status()
            if not self.rich_enabled:
                lines = ["=== DISPOSITIVOS ==="]
                for dev in status:
                    lines.append(f"{dev['name']} - {dev['mode']} - {'BUSY' if dev['busy'] else 'Libre'}")
                return "\n".join(lines)
            table = Table(title="Dispositivos", box=box.ROUNDED if box else None)
            table.add_column("Dispositivo")
            table.add_column("Modo")
            table.add_column("Estado")
            for dev in status:
                table.add_row(dev['name'], dev['mode'], "BUSY" if dev['busy'] else "Libre")
            return table
        if sub in {"on", "off"}:
            if len(args) < 2:
                return "Uso: dev on|off <dispositivo>"
            busy = sub == "on"
            ok, msg = self.os.io_manager.set_busy(args[1], busy)
            return self._styled_feedback(msg, success=ok, title="Dispositivo")
        if sub == "mode":
            if len(args) < 3:
                return "Uso: dev mode <dispositivo> <DMA|PROGRAMADO>"
            ok, msg = self.os.io_manager.set_mode(args[1], args[2])
            return self._styled_feedback(msg, success=ok, title="Dispositivo")
        if sub == "irq":
            if len(args) < 2:
                return "Uso: dev irq <dispositivo> [nivel]"
            level = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
            ok, msg = self.os.trigger_irq(args[1], level)
            return self._styled_feedback(msg, success=ok, title="IRQ")
        if sub == "irq_demo":
            self.os.cpu_scheduler.set_policy("PRIORITY_RR")
            low, _ = self.os.create_process("low", priority=1, memory_size=64)
            if self.rich_enabled:
                self._print(Panel("Preparando proceso de baja prioridad", title="IRQ Demo", border_style="yellow", box=box.ROUNDED if box else None))
            self._print(self._run_scheduler([]))
            self._print(self._styled_feedback("Generando IRQ de Teclado", success=True, title="IRQ"))
            ok, msg = self.os.trigger_irq("teclado", 1)
            self._print(self._styled_feedback(msg, success=ok, title="IRQ"))
            self._print(self._styled_feedback("Reanudando proceso de baja prioridad", success=True, title="CPU"))
            self._print(self._run_scheduler([]))
            return None
        return self._styled_feedback("Subcomando no reconocido", success=False, title="Dispositivo")

    def _io_activate(self, args):
        if not args:
            return "Uso: io <dispositivo> [duración]"
        device = args[0]
        duration = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
        pid = self.os.cpu_scheduler.get_running_process().pid if self.os.cpu_scheduler.get_running_process() else 0
        ok, msg = self.os.io_manager.request_io(pid, device, duration)
        return self._styled_feedback(msg, success=ok, title="E/S")

    def _clear(self, args):
        if self.console:
            self.console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
        return ""

    def _exit(self, args):
        self.os.running = False
        return "Saliendo del simulador..."

    def run(self):
        self._render_banner()
        authenticated = False
        while not authenticated:
            try:
                user = input("Usuario: ").strip()
                if user.lower() in ("exit", "quit"):
                    self._print("Saliendo del simulador...")
                    self.os.running = False
                    return
                pwd = input("Password: ").strip()
                if pwd.lower() in ("exit", "quit"):
                    self._print("Saliendo del simulador...")
                    self.os.running = False
                    return
                success, message = self.os.security_manager.authenticate(user, pwd)
                self.os.log_event("SEGURIDAD", f"Login de {user}: {'OK' if success else 'Fallo'}")
                self._print(self._styled_feedback(message, success, title="Login"))
                if success:
                    authenticated = True
                else:
                    continue
            except KeyboardInterrupt:
                self._print("\n\nSaliendo del simulador...")
                self.os.running = False
                return
        self._print("Escribe 'help' para ver los comandos disponibles\n")
        while self.os.running:
            try:
                command_input = input("OS> ").strip()
                if not command_input:
                    continue
                parts = command_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                if command in self.commands:
                    result = self.commands[command](args)
                    if result is not None:
                        self._print(result)
                else:
                    self._print(self._styled_feedback("Comando no reconocido. Escribe 'help' para ayuda.", success=False, title="Error"))
            except KeyboardInterrupt:
                self._print("\n\nSaliendo del simulador...")
                self.os.running = False
            except Exception as e:
                self._print(f"[red]Error: {e}[/]" if self.rich_enabled else f"Error: {e}")

    def _build_usage_bar(self, percent, width=30, color="blue"):
        percent = max(0, min(100, float(percent)))
        filled = int((percent / 100) * width)
        empty = width - filled
        return f"[{color}]" + "█" * filled + "[/]" + "·" * empty + f" {percent:.1f}%"

    def _styled_feedback(self, message, success=True, title=None):
        if not self.rich_enabled:
            prefix = "✔ " if success else "✖ "
            return f"{prefix}{message}"
        style = self.palette['success'] if success else self.palette['danger']
        panel_title = title or ("Éxito" if success else "Error")
        return Panel(
            message,
            title=panel_title,
            border_style=style,
            box=box.ROUNDED if box else None
        )

    def _render_banner(self):
        if not self.rich_enabled:
            self._print("=" * 60)
            self._print("  SIMULADOR DE SISTEMA OPERATIVO")
            self._print("=" * 60)
            return
        banner_text = "[bold cyan]SIMULADOR DE SISTEMA OPERATIVO[/]\n[bright_black]Gestión de procesos • Memoria • Archivos • CPU[/]"
        panel = Panel(
            banner_text,
            border_style=self.palette['primary'],
            padding=(1, 2),
            box=box.DOUBLE if box else None
        )
        self._print(panel)

    def _print(self, message):
        if self.console:
            self.console.print(message)
        else:
            print(message)
