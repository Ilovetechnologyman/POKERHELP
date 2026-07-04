import tkinter as tk
from tkinter import messagebox, ttk
import threading

from training import TrainingModule


try:
    from treys import Card, Evaluator, Deck
except ImportError:
    pass

class PokerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculateur Poker - Probabilités et EV")
        self.root.geometry("1000x800")
        self.root.minsize(800,600)
        self.root.configure(padx=20, pady=20)

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # Notebook pour onglets
        self.notebook = ttk.Notebook(self.root)
        self.calc_tab = ttk.Frame(self.notebook)
        self.train_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.calc_tab, text="Calculateur")
        self.notebook.add(self.train_tab, text="Entraînement")
        self.notebook.pack(fill="both", expand=True)

        tk.Label(self.calc_tab, text="Poker Stats & EV Calculator", font=("Helvetica", 16, "bold")).pack(pady=10)

        frame_inputs = ttk.LabelFrame(self.calc_tab, text="Paramètres", padding=15)
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

        self.btn_calc = ttk.Button(self.calc_tab, text="🚀 Calculer les Statistiques", command=self.start_calculation)
        self.btn_calc.pack(pady=15, fill="x")

        # Bouton légende
        self.btn_legend = ttk.Button(self.calc_tab, text="ℹ️ Légende", command=self.show_legend)
        self.btn_legend.pack(pady=(0,10))

        # Module d'entraînement externalisé (placé dans l'onglet Entraînement)
        self.training = TrainingModule(self.train_tab, root=self.root)

        # keep references to PhotoImage to avoid GC
        self.card_image_refs = {}

        self.frame_visuals = tk.Frame(self.calc_tab)
        self.frame_visuals.pack(pady=5)

        self.frame_hand_display = tk.Frame(self.frame_visuals)
        self.frame_hand_display.grid(row=0, column=0, padx=10, sticky="n")

        self.frame_board_display = tk.Frame(self.frame_visuals)
        self.frame_board_display.grid(row=0, column=1, padx=10, sticky="n")

        self.progress = ttk.Progressbar(self.calc_tab, mode='indeterminate')

        self.frame_results = ttk.LabelFrame(self.calc_tab, text="Résultats (sur 10 000 simulations)", padding=15)
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

        # Tableau des probabilités par catégorie de main
        tk.Label(self.frame_results, text="Probabilités par catégorie de main :", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(8,2))
        self.tree_probs = ttk.Treeview(self.frame_results, columns=("hand","prob"), show="headings", height=8)
        self.tree_probs.heading("hand", text="Catégorie")
        self.tree_probs.heading("prob", text="Probabilité %")
        self.tree_probs.column("hand", width=200, anchor="w")
        self.tree_probs.column("prob", width=120, anchor="e")
        self.tree_probs.pack(fill="x", pady=2)

    def draw_cards(self, frame, cards_str_list, title):
        for widget in frame.winfo_children():
            widget.destroy()
            
        tk.Label(frame, text=title, font=("Helvetica", 10, "bold")).pack(side="top", pady=2)
        
        cards_frame = tk.Frame(frame, bg="#35654d", padx=5, pady=5, relief="ridge", bd=2)
        cards_frame.pack(side="bottom")
        
        suits = {'s': ('♠', 'black'), 'h': ('♥', '#d60000'), 'd': ('♦', '#d60000'), 'c': ('♣', 'black')}
        
        # try to display images (use training module helper), fallback to text cards
        imgs = []
        for idx, c in enumerate(cards_str_list):
            # attempt image via training module
            img = None
            try:
                img = self.training._get_card_photo(c)
            except Exception:
                img = None

            if img:
                lbl = tk.Label(cards_frame, image=img, bd=1, relief="raised")
                lbl.image = img
                lbl.pack(side="left", padx=3)
                imgs.append(img)
            else:
                if len(c) == 2:
                    val, suit = c[0].upper(), c[1].lower()
                    if val == 'T': val = '10'
                    symbol, color = suits.get(suit, ('?', 'black'))
                    card_lbl = tk.Label(cards_frame, text=f"{val}\n{symbol}", font=("Arial", 16, "bold"), 
                                        bg="white", fg=color, relief="solid", borderwidth=1, width=3, height=2)
                    card_lbl.pack(side="left", padx=3)
                else:
                    card_lbl = tk.Label(cards_frame, text=c, font=("Arial", 14), bg="white", relief="solid", borderwidth=1, width=4, height=2)
                    card_lbl.pack(side="left", padx=3)

        # keep references to avoid garbage collection
        self.card_image_refs[frame] = imgs

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

    def show_legend(self):
        """Affiche une fenêtre expliquant la notation des cartes en français."""
        msg = (
            "Notation des cartes :\n\n"
            "Format : Valeur + Couleur (sans espace).\n"
            "Valeurs : 2-9, T = 10, J = Valet, Q = Dame, K = Roi, A = As.\n"
            "Couleurs : s = pique, h = coeur, d = carreau, c = trèfle.\n\n"
            "Exemples :\n"
            "  Ah -> As de coeur\n"
            "  Ks -> Roi de pique\n"
            "  Td -> 10 de carreau\n\n"
            "Pour une main : entrez 2 cartes séparées par un espace, ex : 'Ah Ks'\n"
            "Pour la table : 0, 3, 4 ou 5 cartes séparées par des espaces, ex : '2h 7s Td'"
        )
        messagebox.showinfo("Légende - Notation des cartes", msg)

    def run_simulation(self, my_hand, my_board, nb_opponents, sb, bb):
        from treys import Evaluator, Deck
        evaluator = Evaluator()
        wins = 0
        ties = 0
        # Compteur des classes de mains (pour le tableau de probabilités)
        hand_class_counts = {}
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
            # classe de la main finale (ex: Straight, Flush, ...)
            try:
                cls = evaluator.get_rank_class(my_score)
            except Exception:
                # fallback si l'API diffère
                cls = None

            if cls is not None:
                hand_class_counts[cls] = hand_class_counts.get(cls, 0) + 1
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
        
        # Calculer les pourcentages par classe et transmettre à l'UI
        hand_probs = {}
        for cls, count in hand_class_counts.items():
            hand_probs[cls] = (count / num_simulations) * 100

        self.root.after(0, self.update_ui, win_rate, tie_rate, loss_rate, ev, mise_joueur, hand_probs)

    def update_ui(self, win_rate, tie_rate, loss_rate, ev, mise_joueur, hand_probs=None):
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

        # Mettre à jour le tableau des probabilités
        for i in self.tree_probs.get_children():
            self.tree_probs.delete(i)

        if hand_probs:
            # Essayer d'obtenir les noms via treys si disponible, sinon fallback FR
            try:
                from treys import Evaluator
                def cls_name(k):
                    try:
                        return Evaluator.class_to_string(k)
                    except Exception:
                        return None
            except Exception:
                def cls_name(k):
                    return None

            fallback = {
                1: "Quinte Flush Royale",
                2: "Quinte Flush",
                3: "Carré",
                4: "Full",
                5: "Couleur",
                6: "Quinte",
                7: "Brelan",
                8: "Deux Paires",
                9: "Paire",
                10: "Carte haute",
            }

            # Trier par classe (meilleure -> pire) si possible
            for cls in sorted(hand_probs.keys()):
                name = cls_name(cls) or fallback.get(cls, f"Classe {cls}")
                prob = hand_probs.get(cls, 0.0)
                self.tree_probs.insert("", "end", values=(name, f"{prob:.2f}%"))
        else:
            # Rien à afficher
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = PokerApp(root)
    root.mainloop()
