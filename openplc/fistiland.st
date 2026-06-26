PROGRAM Fistiland_Main
  VAR
    (* --- CAPTEURS (Écrits par Python, lus par le PLC) --- *)
    Train_En_Gare AT %QX0.0 : BOOL;
    Harnais_Baisse AT %QX0.1 : BOOL;
    
    (* --- ACTIONNEURS (Écrits par le PLC, lus par Python) --- *)
    Ordre_Lancement AT %QX0.2 : BOOL := FALSE;
    Ordre_Freinage AT %QX0.3 : BOOL := TRUE; (* TRUE = Freins fermés par défaut *)
    
    (* --- IHM / CONTRÔLE --- *)
    Bouton_Start_IHM AT %QX0.4 : BOOL := FALSE;
    
    (* --- REGISTRES DE DONNÉES (Vulnérabilité ici) --- *)
    Consigne_Vitesse AT %MW0 : INT := 150; (* Vitesse par défaut en km/h *)
    Erreur_Rollback AT %MW1 : INT := 0;    (* Code 9999 si crash *)
    Force_G AT %MW10 : INT := 0;           (* Sensation passagers *)
  END_VAR

  (* ================================================================= *)
  (* LOGIQUE DU BROYEUR DE NUQUES - FISTILAND (Qualité certifiée)      *)
  (* ================================================================= *)

  (* 1. Séquence de lancement *)
  (* On vérifie que le train est là, que les harnais sont baissés et qu'on appuie sur Start *)
  IF Train_En_Gare AND Harnais_Baisse AND Bouton_Start_IHM THEN
      
      (* --- LA FAILLE CYBER EST ICI --- *)
      (* Normalement, un ingénieur vérifierait: IF Consigne_Vitesse >= 80 THEN... *)
      (* Mais ici, on fait une confiance aveugle au registre %MW0 ! *)
      
      Ordre_Lancement := TRUE;   (* Feu vert pour la catapulte *)
      Ordre_Freinage := FALSE;   (* On ouvre les freins pour laisser partir le train *)
  END_IF;

  (* 2. Réinitialisation du bouton de l'IHM (Anti-maintien) *)
  IF Ordre_Lancement THEN
      Bouton_Start_IHM := FALSE;
  END_IF;

  (* 3. Gestion post-lancement (Simulation très basique) *)
  (* Dès que le train quitte la gare (le capteur passe à FALSE), on coupe la catapulte *)
  IF NOT Train_En_Gare AND Ordre_Lancement THEN
      Ordre_Lancement := FALSE;
  END_IF;

    (* 4. Gestion de la catastrophe (vitesse trop faible) *)
    IF Consigne_Vitesse <= 20 THEN
      Erreur_Rollback := 9999;
      Ordre_Lancement := FALSE; (* On coupe tout *)
      Ordre_Freinage := TRUE;   (* On serre les freins d'urgence en espérant que ça tienne *)
      Bouton_Start_IHM := FALSE;
    END_IF;

END_PROGRAM

(* ================================================================= *)
(* CONFIGURATION MATÉRIELLE POUR OPENPLC                             *)
(* ================================================================= *)
CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    (* Boucle d'exécution du programme toutes les 20 millisecondes *)
    TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : Fistiland_Main;
  END_RESOURCE
END_CONFIGURATION
