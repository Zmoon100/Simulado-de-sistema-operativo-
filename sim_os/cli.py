import os
import time
from datetime import datetime
import random

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
            'fsinfo': ('green', '🗂'),
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
            'meminfo': self._memory_info,
            'top': self._system_info,
            'vmem': self._virtual_memory_info,
            'processflow': self._process_flow,
            'ioinfo': self._io_info,
            'schedpolicy': self._sched_policy,
            'dev': self._dev_command,
            'io': self._io_activate,
            'touch': self._create_file,
            'cat': self._read_file,
            'echo': self._write_file,
            'rm': self._delete_file,
            'ls': self._list_files,
            'schedule': self._run_scheduler,
            'fsinfo': self._fs_info,
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
  processflow <pid>     - Muestra ciclo de vida
  schedule               - Ejecuta el planificador de CPU

Sistema:
  top                   - Muestra información del sistema
  meminfo               - Muestra información de memoria
  vmem                  - Estado de memoria virtual
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
  fsinfo                - Detalle de permisos

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
                "`processflow <pid>` - Ciclo de vida",
                "`schedule` - Ejecuta el planificador",
                "`schedpolicy <FIFO|RR|PRIORITY_RR>` - Cambia política"
            ],
            "Sistema": [
                "`top` - Información general",
                "`meminfo` - Estado de memoria",
                "`vmem` - Memoria virtual",
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
                "`fsinfo` - Permisos"
            ],
            "E/S": [
                "`dev list` - Lista dispositivos",
                "`dev on <dispositivo>` - Activa dispositivo",
                "`dev off <dispositivo>` - Desactiva dispositivo",
                "`dev mode <dispositivo> <DMA|PROGRAMADO>` - Cambia modo",
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

    def _fs_info(self, args):
        files = [self.os.file_system.get_file_info(path) for path in self.os.file_system.files.keys()]
        files = [f for f in files if f]
        if not files:
            return self._styled_feedback("No hay archivos para auditar", success=False, title="FS")
        if not self.rich_enabled:
            lines = ["=== FS INFO ==="]
            for info in files:
                lines.append(f"{info['path']} {info['perms']} {info['owner']}:{info['group']}")
            return "\n".join(lines)
        table = Table(title="Permisos y Hashes", box=box.SIMPLE_HEAVY if box else None)
        table.add_column("Ruta", style="bold")
        table.add_column("Propietario")
        table.add_column("Grupo")
        table.add_column("Permisos")
        table.add_column("Hash SHA256")
        for info in files:
            table.add_row(info['path'], info['owner'], info['group'], info['perms'], info['hash'][:12] + "...")
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
        script = [
            ("Autenticamos al usuario de demo", "login", ["alice", "alice"]),
            ("Mostramos el usuario activo", "whoami", []),
            ("Creamos un proceso web de alta prioridad", "create", ["web", "8", "256"]),
            ("Creamos un proceso de sensores", "create", ["sensor", "5", "128"]),
            ("Listamos procesos para ver NEW→READY", "ps", []),
            ("Consultamos memoria física", "meminfo", []),
            ("Revisamos memoria virtual (paginación/LRU)", "vmem", []),
            ("Ejecutamos el planificador para ver RUNNING y E/S", "schedule", []),
            ("Mostramos el ciclo de vida del proceso web", "processflow", ["{web}"]),
            ("Inspeccionamos dispositivos de E/S", "ioinfo", []),
            ("Creamos un archivo de log de demo", "touch", ["demo_log.txt"]),
            ("Escribimos en el log (simula E/S a disco)", "echo", ["Sistema", "en", "demo", ">", "demo_log.txt"]),
            ("Leemos el log con verificación de integridad", "cat", ["demo_log.txt"]),
            ("Auditamos permisos y hashes del sistema de archivos", "fsinfo", []),
            ("Mostramos la línea de tiempo reciente", "timeline", ["12"])
        ]
        context = {}
        for idx, (description, command, raw_args) in enumerate(script, start=1):
            if command == "demo":
                continue
            resolved_args = self._resolve_demo_args(raw_args, context)
            try:
                handler = self.commands.get(command)
                if not handler:
                    self._print(self._styled_feedback(f"Comando desconocido en demo: {command}", success=False, title="Demo"))
                    continue
                result = handler(resolved_args)
                if result is not None:
                    self._print(result)
            except Exception as exc:
                self._print(self._styled_feedback(f"Demo interrumpida: {exc}", success=False, title="Demo"))
                break
            if command == "create" and resolved_args:
                pid = self._get_pid_by_name(resolved_args[0])
                if pid:
                    context[resolved_args[0]] = pid
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
        files = self.os.file_system.list_files()
        if not files:
            return self._styled_feedback("No hay archivos", success=False, title="Archivos")
        if not self.rich_enabled:
            return "\n".join(files)
        table = Table(title="Archivos en el directorio actual", box=box.SIMPLE_HEAVY if box else None)
        table.add_column("Ruta", style="bold white")
        table.add_column("Permisos")
        table.add_column("Owner")
        for path in files:
            info = self.os.file_system.get_file_info(path) or {}
            table.add_row(path, info.get('perms', '---'), info.get('owner', '?'))
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
            return "Uso: schedpolicy <FIFO|RR|PRIORITY_RR>"
        ok = self.os.cpu_scheduler.set_policy(args[0].upper())
        if not ok:
            return self._styled_feedback("Política no reconocida", success=False, title="Planificador")
        return self._styled_feedback(f"Política cambiada a {self.os.cpu_scheduler.policy}", success=True, title="Planificador")

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
