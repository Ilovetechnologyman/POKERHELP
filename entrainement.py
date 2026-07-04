

class Entrainement:
    
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Create a label for the training module
        self.label = tk.Label(self.frame, text="Module d'entraînement", font=("Helvetica", 16))
        self.label.pack(pady=10)

        # Create a button to start the training module
        self.start_button = tk.Button(self.frame, text="Démarrer l'entraînement", command=self.start_training)
        self.start_button.pack(pady=10)

    def start_training(self):
        # Logic to start the training module goes here
        print("Training module started.")
