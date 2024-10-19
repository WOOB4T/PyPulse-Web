import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup
import threading
import time
import queue
import webbrowser

# crt.sh URL for fetching new domains
crt_sh_url = "https://crt.sh/?q=com&dir=^&sort=1&group=none"

# Parked domain keywords
parked_keywords = ["domain is for sale", "buy this domain", "parked free", "under construction"]

# Function to fetch new domains from crt.sh
def fetch_new_domains(gui_queue):
    gui_queue.put("Fetching new domains from crt.sh...")
    
    try:
        response = requests.get(crt_sh_url)
        if response.status_code != 200:
            gui_queue.put(f"Error fetching crt.sh: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        table_rows = soup.find_all('tr')[1:]
        new_domains = set()
        
        for row in table_rows:
            columns = row.find_all('td')
            if len(columns) >= 6:
                domain = columns[4].text.strip()
                new_domains.add(domain)
        
        return list(new_domains)
    
    except Exception as e:
        gui_queue.put(f"Error: {str(e)}")
        return []

# Function to check domain status
def check_domain_status(domain, gui_queue, tree):
    gui_queue.put(f"Checking domain: {domain}")
    
    try:
        response = requests.get(f"http://{domain}", timeout=5)
        if response.status_code != 200:
            gui_queue.put(f"{domain}: Inactive (HTTP {response.status_code})")
            tree.insert("", "end", values=(domain, "Inactive"))
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text().lower()

        for keyword in parked_keywords:
            if keyword in page_text:
                gui_queue.put(f"{domain}: Parked (Found '{keyword}')")
                tree.insert("", "end", values=(domain, "Parked"))
                return

        word_count = len(page_text.split())
        if word_count < 50:
            gui_queue.put(f"{domain}: Might be parked (Too little content, {word_count} words)")
            tree.insert("", "end", values=(domain, "Parked"))
        else:
            gui_queue.put(f"{domain}: Active (Contains {word_count} words)")
            tree.insert("", "end", values=(domain, "Active"))
    
    except Exception as e:
        gui_queue.put(f"{domain}: Error - {str(e)}")
        tree.insert("", "end", values=(domain, "Error"))

# Background worker function
def run_app(tree, log_text, gui_queue):
    # Fetch new domains and process them
    new_domains = fetch_new_domains(gui_queue)
    
    if new_domains:
        for domain in new_domains:
            check_domain_status(domain, gui_queue, tree)
            time.sleep(1)  # Avoid spamming the server too much

# Function to update the log in real-time
def update_log(main_window, log_text, gui_queue):
    while not gui_queue.empty():
        log_message = gui_queue.get()
        log_text.insert(tk.END, log_message + "\n")
        log_text.see(tk.END)
    main_window.after(100, update_log, main_window, log_text, gui_queue)

# Function to start the process
def start_process(main_window, tree, log_text, gui_queue):
    # Run the app in a new thread to avoid freezing the GUI
    threading.Thread(target=run_app, args=(tree, log_text, gui_queue), daemon=True).start()
    main_window.deiconify()  # Show the main window

# Function to open URL in default browser
def open_in_browser(event):
    item = tree.selection()[0]
    domain = tree.item(item, "values")[0]
    webbrowser.open(f"http://{domain}")

# Function to copy URL to clipboard
def copy_url(event):
    item = tree.selection()[0]
    domain = tree.item(item, "values")[0]
    main_window.clipboard_clear()
    main_window.clipboard_append(f"http://{domain}")

# Function to show context menu
def show_context_menu(event):
    try:
        tree.selection_set(tree.identify_row(event.y))
        popup_menu.tk_popup(event.x_root, event.y_root)
    finally:
        popup_menu.grab_release()

# Create the main window
def create_main_window():
    main_window = tk.Tk()
    main_window.title("Domain Checker GUI")
    main_window.geometry("700x500")

    # Queue for passing messages between threads
    gui_queue = queue.Queue()

    # Frame for logging (Text box)
    log_frame = tk.Frame(main_window)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    log_text = tk.Text(log_frame, wrap=tk.WORD)
    log_text.pack(fill=tk.BOTH, expand=True)

    # Frame for table (Treeview)
    table_frame = tk.Frame(main_window)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    global tree  # Make tree a global variable so it can be accessed in context menu functions
    tree = ttk.Treeview(table_frame, columns=("Domain", "Status"), show="headings")
    tree.heading("Domain", text="Domain")
    tree.heading("Status", text="Status")
    tree.pack(fill=tk.BOTH, expand=True)

    # Create popup menu
    global popup_menu
    popup_menu = tk.Menu(main_window, tearoff=0)
    popup_menu.add_command(label="Open in Browser", command=lambda: open_in_browser(None))
    popup_menu.add_command(label="Copy URL", command=lambda: copy_url(None))

    # Bind right-click event to show_context_menu
    tree.bind("<Button-3>", show_context_menu)

    # Call update_log() to update the log every 100 ms
    main_window.after(100, update_log, main_window, log_text, gui_queue)

    return main_window, tree, log_text, gui_queue

# Create the start window
def create_start_window(main_window, tree, log_text, gui_queue):
    start_window = tk.Toplevel()
    start_window.title("Start Domain Checker")
    start_window.geometry("300x100")

    start_button = tk.Button(start_window, text="Start", 
                             command=lambda: start_process(main_window, tree, log_text, gui_queue))
    start_button.pack(expand=True)

    # Hide the main window initially
    main_window.withdraw()

    start_window.mainloop()

# Main execution
if __name__ == "__main__":
    main_window, tree, log_text, gui_queue = create_main_window()
    create_start_window(main_window, tree, log_text, gui_queue)
    main_window.mainloop()