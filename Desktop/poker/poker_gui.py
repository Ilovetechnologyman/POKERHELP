import tkinter as tk
from tkinter import messagebox, ttk
import threading

try:
    from treys import Card, Evaluator, Deck
except ImportError:
    pass

class PokerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculateur Poker - Probabilités et EV")
        self.root.geometry("500x750")
        self.root.configure(padx=20, pady=20)
        
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        
        tk.Label(root, text="Poker Stats & EV Calculator", font=("Helvetica", 16, "bold")).pack(pady=10)
        
        frame_inputs = ttk.LabelFrame(root, text="Paramètres", padding=15)
        frame_inputs.pack(fill="x", pady=10)
        
        tk.Label(frame_inputs, text="Votre main (ex: Ah Ks) :", font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_hand = ttk.Entry(frame_inputs, width=15)
        self.entry_hand.grid(row=0, column=1, sticky="w", pady=5)
        self.entry_hand.insert(0, "Ah Ks")
        
        tk.Label(frame_inputs, text="Table (Optionnel, ex: 2h 7s Td) :", font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_board = ttk.Entry(frame_inputs, width=15)
        self.entry_board.grid(row=1, column=1, sticky="w", pady=5)
        
        tk.Label(frame_inputs, text="Adversaires (1-3) :", font=("Helvetica", 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.entry_opponents = ttk.Entry(frame_inputs, width=15)
        self.entry_opponents.insert(0, "2")
        self.entry_opponents.grid(row=2, column=1, sticky="w", pady=5)
        
        tk.Label(frame_inputs, text="Petite Blinde (SB) :", font=("Helvetica", 10)).grid(row=3, column=0, sticky="w", pady=5)
        self.entry_sb = ttk.Entry(frame_inputs, width=15)
        self.entry_sb.insert(0, "1")
        self.entry_sb.grid(row=3, column=1, sticky="w", pady=5)
        
        tk.Label(frame_inputs, text="Grosse Blinde (BB) :", font=("Helvetica", 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.entry_bb = ttk.Entry(frame_inputs, width=15)
        self.entry_bb.insert(0, "2")
        self.entry_bb.grid(row=4, column=1, sticky="w", pady=5)
        
        self.btn_calc = ttk.Button(root, text="🚀 Calculer les Statistiques", command=self.start_calculation)
        self.btn_calc.pack(pady=15, fill="x")
        
        self.frame_visuals = tk.Frame(root)
        self.frame_visuals.pack(pady=5)
        
        self.frame_hand_display = tk.Frame(self.frame_visuals)
        self.frame_hand_display.grid(row=0, column=0, padx=10, sticky="n")
        
        self.frame_board_display = tk.Frame(self.frame_visuals)
        self.frame_board_display.grid(row=0, column=1, padx=10, sticky="n")
        
        self.progress = ttk.Progressbar(root, mode='indeterminate')
        
        self.frame_results = ttk.LabelFrame(root, text="Résultats (sur 10 000 simulations)", padding=15)
        self.frame_results.pack(fill="both", expand=True, pady=10)
        
        self.lbl_win = tk.Label(self.frame_results, text="Victoire : --", font=("Helvetica", 12, "bold"), fg="green")
        self.lbl_win.pack(anchor="w", pady=2)
        
        self.lbl_tie = tk.Label(self.frame_results, text="Égalité : --", font=("Helvetica", 12))
        self.lbl_tie.pack(anchor="w", pady=2)
        
        self.lbl_loss = tk.Label(self.frame_results, text="Défaite : --", font=("Helvetica", 12, "bold"), fg="red")
        self.lbl_loss.pack(anchor="w", pady=2)
        
        ttk.Separator(self.frame_results, orient="horizontal").pack(fill="x", pady=10)
        
        self.lbl_ev = tk.Label(self.frame_results, text="Espérance (EV) : --", font=("Helvetica", 12, "bold"))
        self.lbl_ev.pack(anchor="w", pady=2)
        
        self.lbl_advice = tk.Label(self.frame_results, text="Saisissez vos paramètres et lancez le calcul.", font=("Helvetica", 10, "italic"), justify="left")
        self.lbl_advice.pack(anchor="w", pady=5)

    def draw_cards(self, frame, cards_str_list, title):
        for widget in frame.winfo_children():
            widget.destroy()
            
        tk.Label(frame, text=title, font=("Helvetica", 10, "bold")).pack(side="top", pady=2)
        
        cards_frame = tk.Frame(frame, bg="#35654d", padx=5, pady=5, relief="ridge", bd=2)
        cards_frame.pack(side="bottom")
        
        suits = {'s': ('♠', 'black'), 'h': ('♥', '#d60000'), 'd': ('♦', '#d60000'), 'c': ('♣', 'black')}
        
        for c in cards_str_list:
            if len(c) == 2:
                val, suit = c[0].upper(), c[1].lower()
                if val == 'T': val = '10'
                
                symbol, color = suits.get(suit, ('?', 'black'))
                
                card_lbl = tk.Label(cards_frame, text=f"{val}\n{symbol}", font=("Arial", 16, "bold"), 
                                    bg="white", fg=color, relief="solid", borderwidth=1, width=3, height=2)
                card_lbl.pack(side="left", padx=3)

    def start_calculation(self):
        hand_str = self.entry_hand.get().strip().split()
        if len(hand_str) != 2:
            messagebox.showerror("Erreur", "Veuillez entrer exactement 2 cartes séparées par un espace (ex: Ah Ks).")
            return
            
        board_str = self.entry_board.get().strip().split()
        if len(board_str) not in [0, 3, 4, 5]:
            messagebox.showerror("Erreur", "La table doit contenir 0, 3 (flop), 4 (turn) ou 5 (river) cartes.")
            return
            
        try:
            from treys import Card
            my_hand = [Card.new(c) for c in hand_str]
            my_board = [Card.new(c) for c in board_str]
            
            self.draw_cards(self.frame_hand_display, hand_str, "Votre Main")
            if board_str:
                self.draw_cards(self.frame_board_display, board_str, "La Table")
            else:
                for widget in self.frame_board_display.winfo_children():
                    widget.destroy()

        except ImportError:
            messagebox.showerror("Erreur", "La librairie 'treys' n'est pas installée.")
            return
        except Exception as e:
            messagebox.showerror("Erreur", f"Format de carte invalide. Rappel : Valeur (2-9,T,J,Q,K,A) + Couleur (s,h,d,c). \n\nDétail : {str(e)}")
            return
            
        try:
            nb_opponents = int(self.entry_opponents.get().strip())
            sb = float(self.entry_sb.get().strip())
            bb = float(self.entry_bb.get().strip())
        except ValueError:
            messagebox.showerror("Erreur", "Les champs adversaires et blindes doivent être des nombres valides.")
            return
            
        if not (1 <= nb_opponents <= 8):
            messagebox.showwarning("Attention", "Le nombre d'adversaires doit être compris entre 1 et 8.")
            return

        self.btn_calc.config(state="disabled")
        self.progress.pack(fill="x", pady=5)
        self.progress.start()
        
        threading.Thread(target=self.run_simulation, args=(my_hand, my_board, nb_opponents, sb, bb), daemon=True).start()

    def run_simulation(self, my_hand, my_board, nb_opponents, sb, bb):
        from treys import Evaluator, Deck
        evaluator = Evaluator()
        wins = 0
        ties = 0
        num_simulations = 10000

        for _ in range(num_simulations):
            deck = Deck()
            for c in my_hand + my_board:
                if c in deck.cards:
                    deck.cards.remove(c)
                
            opp_hands = [deck.draw(2) for _ in range(nb_opponents)]
            
            cards_to_draw = 5 - len(my_board)
            board = list(my_board)
            if cards_to_draw > 0:
                drawn = deck.draw(cards_to_draw)
                # Une astuce pour prendre en charge de façon robuste la lib treys sans bug "int"/"list"
                if isinstance(drawn, list):
                    board.extend(drawn)
                else:
                    board.append(drawn)
            
            my_score = evaluator.evaluate(board, my_hand)
            opp_scores = [evaluator.evaluate(board, opp) for opp in opp_hands]
            best_opp_score = min(opp_scores)
            
            if my_score < best_opp_score:
                wins += 1
            elif my_score == best_opp_score:
                ties += 1

        win_rate = (wins / num_simulations) * 100
        tie_rate = (ties / num_simulations) * 100
        loss_rate = 100 - win_rate - tie_rate

        pot_initial = sb + bb
        mise_joueur = 3 * bb
        pot_final = pot_initial + mise_joueur + (mise_joueur * nb_opponents)
        gain_net = pot_final - mise_joueur
        ev = ((win_rate/100) * gain_net) - ((loss_rate/100) * mise_joueur)
        
        self.root.after(0, self.update_ui, win_rate, tie_rate, loss_rate, ev, mise_joueur)

    def update_ui(self, win_rate, tie_rate, loss_rate, ev, mise_joueur):
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_calc.config(state="normal")
        
        self.lbl_win.config(text=f"Victoire : {win_rate:.2f}%")
        self.lbl_tie.config(text=f"Égalité : {tie_rate:.2f}%")
        self.lbl_loss.config(text=f"Défaite : {loss_rate:.2f}%")
        
        self.lbl_ev.config(text=f"Espérance (EV) : {ev:.2f} jetons", fg="green" if ev > 0 else "red")
        
        if ev > 0:
            self.lbl_advice.config(text=f"✅ ACTION RENTABLE (EV+) :\nRelancer à {mise_joueur} jetons (3x BB) a un\nretour sur investissement positif à long terme.", fg="green")
        else:
            self.lbl_advice.config(text=f"❌ ACTION DÉFICITAIRE (EV-) :\nInvestir {mise_joueur} jetons (3x BB) pre-flop\navec cette main est une erreur mathématique.", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = PokerApp(root)
    root.mainloop()
