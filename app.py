import random
import os
from openai import OpenAI

# Carica le variabili dal file .env se presente
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# 1. CONFIGURAZIONE API
# La chiave API di OpenAI viene caricata automaticamente dal file .env
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 2. IL LOREBOOK (I mattoncini narrativi)
# Qui ho inserito il tuo esempio. Puoi aggiungere quanti blocchi vuoi tra le virgolette.
ambient = [
"""[Valeburgo, la Città delle Cinque Porte]
Atmosfera: Le mura di pietra nera riflettono la luce tremolante delle torce, mentre l'odore di legna bruciata, spezie e pioggia impregna le strette vie acciottolate. Campane lontane scandiscono le ore e il brusio del mercato si mescola ai sussurri di antiche leggende.
Punti di Interesse: Mercato delle Ombre, Torre dell'Astrologo Reale.
Pericoli e Creature: Ladri della Gilda Nera, mutaforma infiltrati tra i cittadini, gargoyle animati durante la notte e magie proibite nascoste nei sotterranei.
Spunto Narrativo: Ogni luna nuova uno degli antichi portoni cittadini si apre da solo, ma nessuno ricorda cosa si trovi oltre la soglia.""",
"""[Foresta di Sylvaris]
Atmosfera: Una foschia argentata danza tra tronchi giganteschi coperti di muschio luminescente. L'aria profuma di resina e fiori selvatici, mentre canti lontani sembrano provenire dagli alberi stessi.
Punti di Interesse: Lago degli Spiriti Riflessi, Cerchio delle Pietre Cantanti
Pericoli e Creature: Lupi eterei, driadi diffidenti, ragni di cristallo, funghi allucinogeni e sentieri che cambiano posizione con il tramonto.
Spunto Narrativo: Si dice che il cuore della foresta custodisca un albero capace di esaudire un solo desiderio ogni secolo, ma nessuno è mai tornato raccontando la verità.""",
"""[Rovine di Arkanor]
Atmosfera: Colonne spezzate emergono da un mare di erbacce, illuminate da bagliori azzurri che filtrano tra le crepe delle antiche mura. Il silenzio è rotto soltanto dal vento che attraversa archi crollati come un lamento eterno.
Punti di Interesse: Sala del Trono Frantumato, Biblioteca Sepolta
Pericoli e Creature: Cavalieri spettrali, costrutti di pietra ancora attivi, trappole runiche, fantasmi degli antichi maghi e pavimenti instabili.
Spunto Narrativo: Una corona perduta giace ancora tra le rovine, ma ogni esploratore la descrive in un luogo diverso.""",
"""[Abisso di Kar-Dûm]
Atmosfera: Gallerie immense sprofondano nell'oscurità, illuminate da vene di cristalli violacei che pulsano come cuori viventi. L'odore acre di zolfo e pietra umida accompagna il costante gocciolare dell'acqua.
Punti di Interesse: Miniera dei Cristalli Viventi, Lago Nero Sotterraneo
Pericoli e Creature: Troll delle caverne, vermi colossali, pipistrelli vampirici, melme corrosive e improvvisi crolli della roccia.
Spunto Narrativo: Nelle profondità risuona il battito di qualcosa di immenso che nessun minatore ha mai visto, ma tutti hanno sentito.""",
"""[Palude di Nebramorta]
Atmosfera: Nebbie lattiginose coprono acque immobili dove alberi morti emergono come dita scheletriche. L'odore di terra marcia e acqua stagnante rende ogni respiro pesante, mentre strani gorgoglii rompono il silenzio.
Punti di Interesse: Santuario Sommerso, Capanna della Veggente Cieca
Pericoli e Creature: Idre di palude, spiriti inquieti, sciami di insetti velenosi, fuochi fatui ingannatori e sabbie mobili.
Spunto Narrativo: Una voce sussurra il nome di ogni viaggiatore che attraversa la palude, anche se nessuno dovrebbe conoscerlo.""",
"""[Picco di Drakmor]
Atmosfera: Scogliere innevate si innalzano sopra un mare di nuvole, illuminate dal bagliore rossastro di antiche vene laviche. Il vento ulula tra le rocce come un coro di draghi dimenticati e l'aria sa di ghiaccio e cenere.
Punti di Interesse: Fortezza del Drago Spezzato, Tempio delle Fiamme Eterne
Pericoli e Creature: Grifoni selvatici, viverne, elementali del fuoco e del ghiaccio, valanghe improvvise e cultisti al servizio di un antico drago.
Spunto Narrativo: Ogni cento anni il cielo sopra la vetta si apre mostrando una costellazione sconosciuta che indica l'ingresso di un santuario perduto.""",
"""[Deserto di Vhar-Kesh]
Atmosfera: Dune dorate si estendono fino all'orizzonte, illuminate da un sole impietoso durante il giorno e da un cielo colmo di stelle durante la notte. Il vento trasporta granelli di sabbia e un lieve odore di incenso proveniente da antiche rovine sepolte.
Punti di Interesse: Città Sepolta di Ash-Khar, Oasi delle Lune Gemelle
Pericoli e Creature: Scorpioni giganti, mummie risvegliate, serpenti di sabbia, tempeste che cancellano ogni traccia e miraggi incantati.
Spunto Narrativo: Un'intera carovana scompare nello stesso punto del deserto ogni anno, lasciando dietro di sé solo impronte che conducono nel sottosuolo.""",
"""[Isola delle Maree Eterne]
Atmosfera: Onde turchesi si infrangono contro alte scogliere ricoperte di licheni argentati. Il profumo salmastro del mare si mescola a quello dei pini marittimi, mentre il richiamo dei gabbiani nasconde strani canti provenienti dalle profondità.
Punti di Interesse: Faro delle Maree, Grotta del Leviatano
Pericoli e Creature: Sirene, kraken minori, pirati maledetti, granchi corazzati e correnti marine incantate.
Spunto Narrativo: Ogni equinozio emerge un sentiero di pietra sul mare che conduce a un tempio visibile solo per poche ore.""",
"""[Monastero di Rocca Silente]
Atmosfera: Arroccato sulle montagne, il monastero è avvolto da una quiete quasi irreale. Il vento fa vibrare le campane di bronzo e l'aria profuma di pergamena antica, cera e neve.
Punti di Interesse: Archivio delle Mille Pergamene, Giardino delle Statue Vive
Pericoli e Creature: Monaci corrotti dalla magia, spiriti guardiani, gargoyle dormienti e trappole sacre.
Spunto Narrativo: I monaci custodiscono un libro che cambia contenuto ogni alba, predicendo eventi futuri con inquietante precisione.""",
"""[Bosco Cremisi]
Atmosfera: Gli alberi hanno foglie rosso intenso che cadono lentamente anche in piena estate. L'odore dolciastro dei petali copre quello del sangue secco, mentre un incessante fruscio accompagna ogni passo.
Punti di Interesse: Radura del Cuore Rosso, Mulino Abbandonato
Pericoli e Creature: Cervi corrotti, streghe dei rovi, corvi parlanti, liane viventi e alberi predatori.
Spunto Narrativo: Chi raccoglie una foglia cremisi sogna sempre lo stesso volto sconosciuto, che sembra chiedere aiuto.""",
"""[Forgia di Thar-Gor]
Atmosfera: Fiumi di lava scorrono tra giganteschi ponti di ferro annerito. Martelli invisibili risuonano nel vuoto e l'aria è calda, pesante e impregnata di metallo fuso.
Punti di Interesse: Sala delle Incudini Eterne, Camera del Cuore Magmatico
Pericoli e Creature: Golem di ferro, salamandre di fuoco, elementali del magma, esplosioni vulcaniche e automi dimenticati.
Spunto Narrativo: Si narra che l'ultima arma forgiata qui sia in grado di spezzare qualsiasi incantesimo, ma il suo fabbro è scomparso da secoli.""",
"""[Cattedrale delle Stelle Cadute]
Atmosfera: Una maestosa cattedrale in rovina giace sotto un cielo sempre crepuscolare. Frammenti di meteoriti brillano tra le navate distrutte e l'aria vibra di una magia antichissima.
Punti di Interesse: Altare Celeste, Cripta degli Astronomi
Pericoli e Creature: Angeli decaduti, spiriti astrali, costrutti di cristallo, anomalie gravitazionali e magie instabili.
Spunto Narrativo: Ogni stella cadente che colpisce la cattedrale risveglia per una notte un antico custode disposto a rispondere a una sola domanda.""",
"""[Villaggio di Corvoscuro]
Atmosfera: Casette di legno annerito sorgono ai margini di una vallata avvolta dalla nebbia. I camini fumano costantemente e il gracchiare dei corvi accompagna il lento scorrere del tempo.
Punti di Interesse: Locanda del Corvo Nero, Vecchio Cimitero delle Lanterne
Pericoli e Creature: Licantropi, spettri erranti, corvi demoniaci, stregoni erranti e maledizioni familiari.
Spunto Narrativo: Ogni famiglia del villaggio nasconde una stanza murata che nessuno osa aprire da generazioni.""",
"""[Giardino di Aeloria]
Atmosfera: Fiori giganteschi diffondono una luce soffusa che trasforma la notte in un eterno tramonto. L'aria è satura di profumi dolci e il ronzio di insetti luminosi crea una melodia ipnotica.
Punti di Interesse: Serra della Regina Fatata, Fontana dei Petali Eterni
Pericoli e Creature: Fate ingannatrici, api giganti, mandragore, piante carnivore e pollini che alterano la memoria.
Spunto Narrativo: Si racconta che nel giardino sbocci un unico fiore capace di riportare in vita un'anima perduta, ma appassisce appena viene osservato."""
]

npc = [
"""[Garrick - Fabbro Runico]
Aspetto e Atteggiamento: Un nano burbero con la barba bruciacchiata e mani coperte di fuliggine. Parla a scatti e fissa sempre le armi altrui per valutarne la fattura.
Motivazione/Segreto: Ha forgiato lui un'arma per i Ladri della Gilda Nera e ora se ne pente.
Utilità per il Giocatore: Può riparare armi gratuitamente se il giocatore si dimostra nemico della Gilda, oppure può fornire informazioni preziose sui loro nascondigli.""",
"""[Aldren Corvoscuro] - Cavaliere Errante
Aspetto e Atteggiamento: Indossa un'armatura consumata dal tempo, ricoperta di graffi profondi e stemmi ormai irriconoscibili. Mantiene sempre una postura impeccabile e parla con calma, come se pesasse ogni parola.
Motivazione/Segreto: Cerca disperatamente il sovrano a cui un tempo giurò fedeltà, ignaro che questi sia morto da secoli. Porta con sé una reliquia che molti ordini sono disposti a uccidere pur di ottenere.
Utilità per il Giocatore: Può addestrare nelle tecniche di combattimento, scortare durante missioni pericolose e riconoscere antichi simboli nobiliari.""",
"""[Lyssara] - Mercante di Curiosità Arcane
Aspetto e Atteggiamento: Una donna dagli occhi color ambra e dai lunghi capelli argentati raccolti in elaborate trecce. Sorride spesso, ma il suo sguardo sembra analizzare ogni dettaglio di chi le sta davanti.
Motivazione/Segreto: Colleziona manufatti magici per ricomporre un antico artefatto distrutto. Alcuni degli oggetti che vende sono stati sottratti a tombe proibite.
Utilità per il Giocatore: Vende reliquie magiche, pergamene rare, ingredienti alchemici e può identificare oggetti incantati.""",
"""[Fratello Edric] - Monaco Guaritore
Aspetto e Atteggiamento: Indossa una semplice tunica di lino con un rosario di pietra bianca appeso alla cintura. Ha mani segnate dal lavoro e uno sguardo sereno che ispira immediata fiducia.
Motivazione/Segreto: Vuole impedire il ritorno di una piaga magica che devastò il suo monastero. Conserva in segreto un grimorio proibito che potrebbe salvarlo... o condannarlo.
Utilità per il Giocatore: Cura ferite e maledizioni minori, prepara rimedi naturali e conosce antichi rituali sacri.""",
"""[Marek il Sussurratore] - Informatore
Aspetto e Atteggiamento: Magro e sempre avvolto in un mantello scuro, compare e scompare tra la folla senza fare rumore. Parla sottovoce e conclude ogni frase con un sorriso enigmatico.
Motivazione/Segreto: Vende informazioni al miglior offerente, ma sta segretamente raccogliendo prove contro una potente confraternita criminale.
Utilità per il Giocatore: Rivela pettegolezzi, posizioni di bersagli, passaggi nascosti e missioni secondarie.""",
"""[Brunna Forgiabrace] - Fabbra Nanica
Aspetto e Atteggiamento: Bassa e robusta, porta una folta treccia color rame annerita dalla fuliggine della forgia. Ride fragorosamente mentre lavora il metallo con impressionante precisione.
Motivazione/Segreto: Vuole creare l'arma perfetta per onorare il padre scomparso. Possiede un frammento di metallo celeste che nessuno dovrebbe sapere esista.
Utilità per il Giocatore: Forgia e ripara armi e armature, migliora equipaggiamenti e riconosce materiali rari.""",
"""[Selene Velombra] - Ranger
Aspetto e Atteggiamento: Un'elfa dai capelli corvini e dagli occhi verde smeraldo, sempre accompagnata da un grande falco. Osserva ogni dettaglio dell'ambiente prima di parlare.
Motivazione/Segreto: È sulle tracce di una creatura che ha distrutto il suo villaggio. In realtà conosce un antico sentiero che conduce al regno delle fate, ma ne custodisce gelosamente l'accesso.
Utilità per il Giocatore: Guida attraverso foreste e montagne, individua tracce, evita imboscate e insegna tecniche di sopravvivenza.""",
"""[Orik Doppio Volto] - Oste
Aspetto e Atteggiamento: Un uomo corpulento dalla barba grigia e dall'aria bonaria che accoglie tutti con una risata fragorosa. Dietro il bancone ascolta ogni conversazione senza mai sembrare interessato.
Motivazione/Segreto: Gestisce una rete segreta di messaggeri e contrabbandieri che opera sotto la sua locanda. Protegge una persona ricercata nascosta nelle cantine.
Utilità per il Giocatore: Offre alloggio, raccoglie informazioni provenienti da tutto il regno e può mettere in contatto con individui difficili da trovare.""",
"""[Neria dell'Eclisse] - Maga Errante
Aspetto e Atteggiamento: Indossa lunghe vesti blu notte ricamate con costellazioni argentate e porta un bastone sormontato da un cristallo nero. Il suo volto tradisce un'antica stanchezza, ma i suoi occhi brillano di immensa conoscenza.
Motivazione/Segreto: Cerca un rituale capace di fermare una profezia che annuncia la distruzione del mondo. È stata un tempo membro dell'ordine responsabile della stessa catastrofe che ora tenta di evitare.
Utilità per il Giocatore: Traduce rune antiche, insegna incantesimi, identifica fenomeni magici e apre portali verso luoghi dimenticati.""",
"""[Dorian Pietragrigia] - Cacciatore di Taglie
Aspetto e Atteggiamento: Un uomo massiccio con una barba intrecciata e un mantello di pelliccia logoro. Osserva chiunque come se ne stesse già valutando il prezzo sulla propria lista di taglie.
Motivazione/Segreto: Vuole catturare il criminale che ha assassinato suo fratello, senza sapere che l'uomo ora vive sotto una nuova identità.
Utilità per il Giocatore: Offre missioni di caccia, conosce i rifugi dei fuorilegge e può rintracciare persone scomparse.""",
"""[Elyra Lunargento] - Astrologa
Aspetto e Atteggiamento: Indossa abiti ricamati con simboli celesti e porta sempre con sé un astrolabio d'argento. Parla con voce calma e spesso interrompe una conversazione per osservare il cielo.
Motivazione/Segreto: Cerca una stella scomparsa dalle mappe celesti, convinta che sia in realtà un antico dio imprigionato.
Utilità per il Giocatore: Interpreta presagi, individua date favorevoli e rivela informazioni su eventi cosmici e magie astrali.""",
"""[Kragh] - Mercenario Orco
Aspetto e Atteggiamento: Alto quasi due metri e coperto di cicatrici, porta una gigantesca ascia sulla schiena. Non ama parlare, ma mantiene sempre la parola data.
Motivazione/Segreto: Sta accumulando denaro per riscattare il proprio clan ridotto in schiavitù.
Utilità per il Giocatore: Può essere assunto come guardia del corpo, aiutare nei combattimenti più difficili e addestrare nell'uso delle armi pesanti.""",
"""[Sorella Miriam] - Custode del Santuario
Aspetto e Atteggiamento: Una donna anziana dai capelli candidi e dal volto segnato dal tempo, sempre circondata dal profumo di erbe medicinali. Accoglie chiunque con gentilezza, ma il suo sorriso svanisce quando si parla del passato.
Motivazione/Segreto: Protegge un antico sigillo nascosto sotto il santuario, temendo il ritorno di una creatura dimenticata.
Utilità per il Giocatore: Benedice equipaggiamenti, rimuove maledizioni e offre rifugio sicuro.""",
"""[Finn Rattosvelto] - Ladro
Aspetto e Atteggiamento: Un giovane agile dai capelli arruffati e dal sorriso sfacciato, con decine di grimaldelli nascosti tra gli abiti. Non resta mai fermo e tamburella continuamente le dita.
Motivazione/Segreto: Ha rubato un anello apparentemente insignificante che appartiene a un potente signore oscuro.
Utilità per il Giocatore: Scassina serrature, disinnesca trappole e recupera oggetti difficili da ottenere.""",
"""[Thalia Erbaverde] - Erborista
Aspetto e Atteggiamento: Una giovane donna con lunghi capelli castani intrecciati con foglie e piccoli fiori. Ha mani sempre macchiate di linfa e parla con entusiasmo di ogni pianta che incontra.
Motivazione/Segreto: È alla ricerca del Fiore dell'Alba, una pianta leggendaria che potrebbe guarire qualsiasi malattia.
Utilità per il Giocatore: Prepara pozioni, antidoti, veleni naturali e identifica piante rare.""",
"""[Varok il Collezionista] - Antiquario
Aspetto e Atteggiamento: Elegante e impeccabile, indossa guanti di velluto per non toccare direttamente gli oggetti antichi. Il suo negozio è stipato di reliquie provenienti da ogni angolo del regno.
Motivazione/Segreto: Colleziona manufatti appartenuti ai Re Stregoni nel tentativo di ricostruire la loro storia... e il loro potere.
Utilità per il Giocatore: Acquista tesori, valuta reperti e fornisce informazioni sulla loro origine.""",
"""[Ysolde Nebbiabianca] - Veggente
Aspetto e Atteggiamento: Una donna cieca dagli occhi lattiginosi che cammina senza bastone come se vedesse oltre il mondo materiale. Una lieve nebbia sembra seguirla ovunque.
Motivazione/Segreto: Le sue visioni stanno diventando sempre più oscure e mostrano un volto che riconosce come il proprio, ma molto più giovane.
Utilità per il Giocatore: Offre profezie, interpreta sogni, individua oggetti perduti e suggerisce possibili conseguenze delle decisioni.""",
"""[Brom Barilferro] - Oste
Aspetto e Atteggiamento: Un nano robusto dal naso rosso e dalla barba intrecciata con anelli di rame. Accoglie ogni cliente con una pinta già pronta e una battuta sempre diversa.
Motivazione/Segreto: La sua locanda è costruita sopra un'antica cripta nanica che tiene nascosta a tutti.
Utilità per il Giocatore: Fornisce informazioni sui viaggiatori, offre camere sicure e mette in contatto con avventurieri in cerca di compagnia.""",
"""[Caelis Ventoquieto] - Bardo
Aspetto e Atteggiamento: Indossa un mantello blu ricamato con note musicali dorate e porta un liuto antico sempre accordato. Ha una parlantina irresistibile e sembra conoscere una storia su chiunque.
Motivazione/Segreto: Cerca la Ballata Perduta, una melodia capace di piegare la volontà dei draghi.
Utilità per il Giocatore: Diffonde la reputazione dell'eroe, raccoglie notizie nelle taverne e conosce leggende dimenticate.""",
"""[Helga Rocciadura] - Carovaniera
Aspetto e Atteggiamento: Una donna alta e muscolosa con un mantello impolverato e stivali consumati da migliaia di chilometri. Trasmette sicurezza e affronta ogni imprevisto con sorprendente calma.
Motivazione/Segreto: Sta cercando una rotta commerciale perduta che conduce a una città considerata soltanto una leggenda.
Utilità per il Giocatore: Organizza viaggi, vende mappe aggiornate, trasporta merci e conosce le strade più sicure del continente."""
]

creature = [
"""[Gargoyle d'Ossidiana]
Descrizione e Pericolosità: Una mostruosità alata alta due metri, scolpita in pura pietra nera. I suoi artigli tagliano l'acciaio.
Comportamento: Resta immobile come una statua sui tetti per tutto il giorno, si anima solo di notte per piombare silenziosamente sulle prede.
Punto Debole: Le giunture delle ali sono fragili. Un colpo contundente forte (come un martello) le spezza facilmente.
Possibile Bottino (Loot): Polvere di pietra magica (utile in alchimia), Cuore d'Ossidiana (gemma preziosa).""",
"""[Lupo delle Nebbie]
Descrizione e Pericolosità: Un enorme lupo dal pelo grigio-argento, con occhi azzurri che brillano attraverso la foschia. È rapido, silenzioso e letale, capace di abbattere un uomo prima che riesca a estrarre la spada.
Comportamento: Caccia in piccoli branchi e sfrutta la nebbia per isolare le prede. Attacca solo quando è certo di avere il vantaggio.
Punto Debole: Il suo olfatto estremamente sensibile viene confuso dal fumo intenso e dagli aromi pungenti.
Possibile Bottino (Loot): Pelle argentata, zanne affilate, occhi incantati utilizzabili per pozioni di visione notturna.""",
"""[Ragno di Cristallo]
Descrizione e Pericolosità: Un ragno gigantesco ricoperto da un esoscheletro trasparente simile al quarzo. I suoi morsi iniettano un veleno che irrigidisce lentamente il corpo della vittima.
Comportamento: Tesse ragnatele quasi invisibili tra rocce e alberi, aspettando pazientemente che la preda rimanga intrappolata.
Punto Debole: Le vibrazioni improvvise lo disorientano, rendendolo vulnerabile.
Possibile Bottino (Loot): Filo di cristallo, ghiandola velenifera, frammenti del carapace.""",
"""[Golem di Basalto]
Descrizione e Pericolosità: Un colosso di pietra nera attraversato da vene incandescenti. Ogni suo colpo è in grado di frantumare muri e armature.
Comportamento: Difende instancabilmente rovine, templi o tesori e non si ferma finché l'intruso non viene eliminato.
Punto Debole: Le rune incise sulla schiena alimentano la sua magia e possono essere danneggiate.
Possibile Bottino (Loot): Nucleo elementale, frammenti runici, minerali rari.""",
"""[Sirena Abissale]
Descrizione e Pericolosità: Una figura elegante dalla pelle azzurro pallido e dai lunghi capelli algosi, con occhi completamente neri. Il suo canto trascina i viaggiatori verso acque profonde da cui nessuno riemerge.
Comportamento: Seduce le vittime con melodie ipnotiche prima di trascinarle sott'acqua.
Punto Debole: Non può usare il proprio canto contro chi è completamente sordo o protegge l'udito.
Possibile Bottino (Loot): Perla incantata, squame luminose, conchiglia melodica.""",
"""[Idra delle Paludi]
Descrizione e Pericolosità: Un enorme rettile anfibio con numerose teste ricoperte di melma verde scuro. Ogni testa può mordere indipendentemente e rigenera rapidamente le ferite.
Comportamento: Rimane nascosta sotto l'acqua torbida aspettando che le prede si avvicinino alla riva.
Punto Debole: Le ferite cauterizzate con fuoco impediscono la rigenerazione delle teste.
Possibile Bottino (Loot): Sangue rigenerante, denti affilati, pelle resistente all'umidità.""",
"""[Spettro del Giuramento]
Descrizione e Pericolosità: Un guerriero etereo avvolto da un'armatura consumata e da una luce bluastra. La sua lama attraversa la carne e colpisce direttamente l'anima.
Comportamento: Sorveglia tombe e reliquie, attaccando chiunque violi il proprio giuramento sacro.
Punto Debole: Recitare il giuramento che protegge o restituire un oggetto sacro può placare il suo spirito senza combattere.
Possibile Bottino (Loot): Essenza spettrale, spada benedetta, frammenti di armatura eterea.""",
"""[Divoratore d'Ombre]
Descrizione e Pericolosità: Una creatura informe composta da oscurità liquida, con decine di occhi luminosi che si aprono e chiudono sulla sua superficie. Dove passa, la luce sembra svanire completamente.
Comportamento: Si muove tra le ombre e assorbe lentamente l'energia vitale delle vittime prima di colpire.
Punto Debole: La luce intensa o gli incantesimi luminosi dissolvono temporaneamente il suo corpo.
Possibile Bottino (Loot): Essenza d'ombra, cristallo oscuro, residui magici utilizzabili negli incantesimi.""",
"""[Drago delle Tempeste]
Descrizione e Pericolosità: Un gigantesco drago dalle scaglie blu acciaio attraversate da scariche elettriche. Il battito delle sue ali scatena venti devastanti e fulmini che inceneriscono interi gruppi di avventurieri.
Comportamento: Difende il proprio territorio dall'alto, colpendo con fulmini prima di piombare sulle prede.
Punto Debole: Durante il volo accumula enormi quantità di energia elettrica; costringerlo ad atterrare lo rende molto meno pericoloso.
Possibile Bottino (Loot): Scaglie draconiche, artigli, cuore del fulmine, tesoro accumulato nel covo.""",
"""[Mimic del Tesoriere]
Descrizione e Pericolosità: All'apparenza è un normale baule rinforzato con ferro, ma quando una vittima si avvicina rivela una bocca colma di denti e una lunga lingua adesiva. È sorprendentemente veloce e può spezzare un braccio con un solo morso.
Comportamento: Rimane immobile per giorni fingendosi un contenitore abbandonato, colpendo solo quando la preda abbassa la guardia.
Punto Debole: Detesta il sale e le sostanze corrosive, che lo costringono ad aprirsi prima di attaccare.
Possibile Bottino (Loot): Denti affilatissimi, saliva adesiva, monete e oggetti appartenuti alle sue vittime.""",
"""[Basilisco di Pietrascura]
Descrizione e Pericolosità: Un enorme rettile dalle scaglie color ardesia e dagli occhi giallo oro. Il suo sguardo può trasformare lentamente carne e pietra in un'unica massa rocciosa.
Comportamento: Difende il proprio territorio con pazienza, inseguendo le vittime solo dopo averle indebolite con il suo sguardo.
Punto Debole: Evita di guardare superfici riflettenti, che possono rimandargli contro il proprio potere.
Possibile Bottino (Loot): Occhi di basilisco, veleno pietrificante, scaglie resistenti.""",
"""[Falena del Sogno]
Descrizione e Pericolosità: Un enorme insetto dalle ali iridescenti ricoperte di polvere luminosa. Non è aggressiva di per sé, ma il suo pulviscolo induce sonni profondi e incubi mortali.
Comportamento: Vola silenziosamente nelle ore notturne attirata da luci e fuochi da campo.
Punto Debole: Il vento forte disperde il suo pulviscolo e la rende incapace di difendersi.
Possibile Bottino (Loot): Polvere onirica, ali luminose, antenne magiche.""",
"""[Verme delle Profondità]
Descrizione e Pericolosità: Un gigantesco verme cieco lungo decine di metri, ricoperto da placche ossee. Le suas fauci possono inghiottire un cavallo intero.
Comportamento: Percepisce le vibrazioni del terreno e tende imboscate emergendo improvvisamente dal sottosuolo.
Punto Debole: Le esplosioni o i forti rumori ne disorientano i sensi.
Possibile Bottino (Loot): Denti enormi, pelle resistente, ghiandole digestive utilizzate dagli alchimisti.""",
"""[Custode Runico]
Descrizione e Pericolosità: Un'armatura vuota animata da antiche rune dorate, priva di qualsiasi essere vivente al suo interno. Combatte con precisione perfetta e non conosce paura né fatica.
Comportamento: Pattuglia incessantemente sale sacre e cripte dimenticate, eliminando chiunque oltrepassi determinati sigilli.
Punto Debole: Distruggere o cancellare la runa principale sul suo elmo interrompe l'incantesimo che lo anima.
Possibile Bottino (Loot): Rune magiche, armatura incantata, frammenti di metallo antico.""",
"""[Arpia Cinerea]
Descrizione e Pericolosità: Una creatura alata dal volto umano e dagli artigli ricurvi come falci. Le sue urla penetranti possono far perdere l'equilibrio anche ai guerrieri più esperti.
Comportamento: Vive sulle scogliere e attacca in stormi, cercando di spingere le prede nel vuoto.
Punto Debole: Le ali sono fragili e facilmente danneggiabili da frecce o reti.
Possibile Bottino (Loot): Piume magiche, artigli, corde intrecciate recuperate dai nidi.""",
"""[Fungo Colossale]
Descrizione e Pericolosità: Un enorme fungo ambulante alto quanto un uomo, ricoperto di spore verdastre. Il suo corpo è lento, ma ogni colpo libera nuvole tossiche.
Comportamento: Si muove lentamente nelle caverne umide e difende il proprio territorio tramite spore velenose.
Punto Debole: Il fuoco secca rapidamente il suo corpo impedendogli di rilasciare nuove spore.
Possibile Bottino (Loot): Spore medicinali, cappello fungino gigante, essenza micotica.""",
"""[Cervo Spettrale]
Descrizione e Pericolosità: Un maestoso cervo dal corpo traslucido e dalle corna luminose come il chiaro di luna. Normalmente evita il conflitto, ma diventa estremamente aggressivo se il bosco viene profanato.
Comportamento: Appare e scompare tra gli alberi, attirando gli intrusi in luoghi da cui è impossibile uscire.
Punto Debole: Offerte di acqua pura o il ripristino dell'equilibrio naturale possono placarne l'ira.
Possibile Bottino (Loot): Corna eteree, essenza spirituale, muschio sacro.""",
"""[Lich del Sepolcro Eterno]
Descrizione e Pericolosità: Uno scheletro avvolto in vesti regali consumate, con occhi che brillano di una luce viola innaturale. È uno dei maghi più pericolosi esistenti, capace di controllare orde di non morti.
Comportamento: Evita il combattimento diretto, preferendo evocare servitori e lanciare potenti incantesimi da lontano.
Punto Debole: Finché il suo filatterio rimane intatto, tornerà sempre in vita; distruggerlo è l'unico modo per eliminarlo definitivamente.
Possibile Bottino (Loot): Grimorio proibito, bastone necromantico, gemme oscure, filatterio.""",
"""[Fenice Cinerea]
Descrizione e Pericolosità: Un enorme uccello dalle piume nere percorse da braci incandescenti. Ogni battito d'ali solleva cenere rovente e lingue di fuoco.
Comportamento: È territoriale e attacca chiunque si avvicini al proprio nido, ma evita combattimenti inutili.
Punto Debole: Durante la rinascita dalle proprie ceneri rimane vulnerabile per pochi istanti.
Possibile Bottino (Loot): Piume della Fenice, cenere rigenerante, uovo incandescente."""
]

# 3. IL MOTORE LOGICO (Python estrae i dati a caso)
ambient_scelta = random.choice(ambient)
npc_scelto = random.choice(npc)
creatura_scelta = random.choice(creature)

# 4. IL MEGA-PROMPT DI SISTEMA
sistema = f"""Sei il Dungeon Master di un'avventura testuale fantasy medievale.
Il tuo compito è creare un'avventura logica e immersiva usando ESCLUSIVAMENTE gli elementi forniti qui sotto.

=== ELEMENTI DELLA SCENA ===

AMBIENTAZIONE:
{ambient_scelta}

PERSONAGGIO PRESENTE O COINVOLTO:
{npc_scelto}

CREATURA O NEMICO NELLE VICINANZE:
{creatura_scelta}

=== ISTRUZIONI ===
1. Avvio: Genera un breve prologo. Metti il giocatore subito dentro l'ambientazione e usa lo "Spunto Narrativo" o il "Personaggio" per creare un problema immediato da risolvere.
2. Regole: Valuta le azioni del giocatore usando la logica, non usare dadi virtuali. Se il giocatore è astuto (es. sfrutta il "Punto Debole" della creatura), fallo vincere. Se vince un combattimento, descrivi il "Possibile Bottino".
3. Formato: Sii immersivo ma conciso. Usa l'atmosfera descritta per colorare la narrazione.
4. Chiusura: Termina SEMPRE ogni tuo messaggio chiedendo: "Cosa fai?".
"""

# 5. INIZIALIZZAZIONE DELLA MEMORIA (L'array che salva la conversazione)
chat_history = [
    {"role": "system", "content": sistema}
]

print("="*50)
print(" MORPHEUS GENESIS LITE - AVVIO SISTEMA ")
print("="*50)
print("(Creazione del mondo in corso, attendi il prologo del DM...)\n")

# 6. IL CICLO DI GIOCO PRINCIPALE
while True:
    try:
        # L'IA pensa e risponde
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Puoi cambiare modello in gpt-4o se preferisci
            messages=chat_history,
            temperature=0.7 # 0.7 è un buon equilibrio tra logica e creatività
        )
        
        # Estrazione della risposta
        dm_reply = response.choices[0].message.content
        print(f"\nDUNGEON MASTER:\n{dm_reply}\n")
        
        # Salvataggio nella memoria
        chat_history.append({"role": "assistant", "content": dm_reply})
        
        # Turno del giocatore
        player_input = input("AZIONE (scrivi 'esci' per terminare): ")
        
        if player_input.lower() in ["esci", "quit", "exit"]:
            print("\nGrazie per aver giocato. Partita terminata.")
            break
            
        # Salvataggio dell'azione nella memoria
        chat_history.append({"role": "user", "content": player_input})

    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        break