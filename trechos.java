// =============================================================================================================================
// =============================================================================================================================
//=========[ Função Temporizadora ]========= Temporiza com tratamento de erros
public void tempo(int valor){
       if(valor >= 0) {
           try {
               Thread.sleep(valor);
           } catch (InterruptedException e) {
               Thread.currentThread().interrupt();
           }
       }
   }

// =============================================================================================================================
// =============================================================================================================================
//=========[ Função Limpa Tela ]========= Ela limpa o terminal
public static void limpar() {
    try {
        if (System.getProperty("os.name").contains("Windows")) {
            new ProcessBuilder("cmd", "/c", "cls").inheritIO().start().waitFor();
        } else {
            System.out.print("\033[H\033[2J");
            System.out.flush();
        }
    } catch (Exception e) {
        for (int i = 0; i < 50; i++) System.out.println();
    }
}

// =============================================================================================================================
// =============================================================================================================================
//=========[ Change Code Page ]========= Função que muda o chcp para chcp 65001 sem digitar o comando diretamente no terminal
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;


    public static void chcp() {
        try {
            System.setOut(new PrintStream(System.out, true, StandardCharsets.UTF_8));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

// =============================================================================================================================
