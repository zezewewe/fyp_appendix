// [Inference] Initialize Station Mode Setup and Scan for Recognised APs based on RSSI and Channel
// Reference made to https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html

#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "esp_wifi.h"
#include "esp_log.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"

#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"

#include "lwip/sockets.h"
#include "lwip/dns.h"
#include "lwip/netdb.h"
#include "lwip/err.h"
#include "lwip/sys.h"
#include <lwip/netdb.h>

#include "mqtt_client.h"
#include <math.h>

#define DEFAULT_SCAN_LIST_SIZE 15 // Number of APs to scan
#define AP_ID_INDEX 6 // Number of FYP access points

#define ESP_WIFI_SSID     /*Name of LAN to connect to*/
#define ESP_WIFI_PASS     /*Password of LAN connection*/

static const char *TAG_SCAN = "Scan";
static const char *TAG_STATISTICS = "Statistics";
static const char *TAG_UDP = "UDP";

#define NUM_READINGS_PER_ITER 10 // 40 readings at each location

#define MAX_BUFFER_SIZE  1024

// Laptop Host (Python)
#define LAPTOP_IP_ADDR1     "192.168.3.57" // Localization Waypoint Robot
#define LAPTOP_IP_ADDR2     "192.168.1.102" // Localization XPS13 MAC: 9C-B6-D0-9A-15-B7
#define LAPTOP_IP_PORT1     4210
#define LAPTOP_IP_PORT2     4200

// ID MAC LocalizationNetwork HomeNetwork Port
// ESP-L 10:97:bd:d5:5e:38 192.168.3.200 192.168.1.100 4220
// ESP-R 40:91:51:23:16:0c 192.168.3.201 192.168.1.101 4230
// XPS13 9C-B6-D0-9A-15-B7 192.168.3.202 192.168.1.102 4200

// Left / 1
#define ESP32_IP_ADDR     "192.168.1.100" // MAC: 10:97:bd:d5:5e:38
#define ESP32_IP_PORT     4220 

// Right / 2
// #define ESP32_IP_ADDR     "192.168.1.101" // MAC: 40:91:51:23:16:0c 
// #define ESP32_IP_PORT     4230 

#define ESP_STA_CHAR      'L'

    
// 1 - Wi-Fi/LwIP Init 
static void wifi_init(void) { 
    // Initialize TCP/IP stack, Event loop, Set ESP as STA/AP, Initialize default config, Start station

    ESP_ERROR_CHECK(esp_netif_init()); // Initialize underlying TCP/IP stack
    ESP_ERROR_CHECK(esp_event_loop_create_default()); // Create default event loop
    esp_netif_t *sta_netif = esp_netif_create_default_wifi_sta(); // Create default WIFI STA
    assert(sta_netif); // if sta_netif is zero, assert macro writes message to stderr and terminates program by calling abort

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT(); // Initialize configuration to default values 
    ESP_ERROR_CHECK(esp_wifi_init(&cfg)); // Init Wifi Allocate resource for WiFi driver
}

// 2 - Wi-Fi Start
static void wifi_start(void) {
    ESP_ERROR_CHECK(esp_wifi_start()); // Start WiFi -> for WIFI_MODE_STA, it creates station control block and start station
}

// 3 - Wifi Configs 
wifi_scan_config_t scan_config = {
            .ssid = NULL,
            .bssid = NULL,
            .show_hidden = false,
            .channel = 1, // scan specifically channel 1
            .scan_type = WIFI_SCAN_TYPE_ACTIVE 
};

static void event_handler(void* event_handler_arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data) {
    switch (event_id) {
        case WIFI_EVENT_STA_START:
            printf("WiFi connecting ... \n");
            break;
        case WIFI_EVENT_STA_CONNECTED:
            printf("WiFi connected ... \n");
            break;
        case WIFI_EVENT_STA_DISCONNECTED:
            printf("WiFi lost connection ... \n");
            break;
        case IP_EVENT_STA_GOT_IP:
            printf("WiFi got IP ... \n\n");
            break;
        default:
            break;
    }
}

static void wifiConnectConfig(void){
    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &event_handler, NULL, &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &event_handler, NULL, &instance_got_ip));
    wifi_config_t wifi_config = {
            .sta = {
                .ssid = ESP_WIFI_SSID,
                .password = ESP_WIFI_PASS,
            },
    };
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );
}

static void wifiConnect(void){
    ESP_ERROR_CHECK(esp_wifi_connect() );
}

static void wifiDisconnect(void){
    ESP_ERROR_CHECK(esp_wifi_disconnect() );
}

// c - Scan and identify 3 APs and update array over many iterations in the same location
static void scanReadFypApsAndDisplay(int8_t (*arr)[NUM_READINGS_PER_ITER], int idx) {
    // Output: RSSI value of 3 fyp APs 
    // printf("\n%i:idx",idx);
    uint16_t number = DEFAULT_SCAN_LIST_SIZE;
    wifi_ap_record_t ap_info[number]; // Number of APs to scan
    memset(ap_info, 0, sizeof(ap_info)); // Initialize ap_info with zeros

    int unknown_AP_start_pointer = AP_ID_INDEX;
    uint16_t ap_count = 0;

    esp_wifi_scan_start(&scan_config, true); // Scan all available APs
    ESP_ERROR_CHECK(esp_wifi_scan_get_ap_records(&number, ap_info)); // Get AP list found in last scan, AP info can be found here: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html#_CPPv416wifi_ap_record_t
    ESP_ERROR_CHECK(esp_wifi_scan_get_ap_num(&ap_count));
    
    uint8_t mask_ssid[3] = {'f','y','p'}; // SSID characters to compare
    for (int i = 0; i < DEFAULT_SCAN_LIST_SIZE; i++) {
        uint8_t rssiVal = (unsigned)(-ap_info[i].rssi);
        int known_ssid_sum = memcmp(ap_info[i].ssid,mask_ssid,sizeof mask_ssid); // Identify if SSID is recognised
        if (known_ssid_sum == 0) {  // Known AP
            int8_t tmp_ssid = (int8_t)(*(ap_info[i].ssid+3))-48; // dereferencing ssid array and obtaining the unique ap id (i.e. [1,ap_id_index])
            // printf("\ntmp_ssid:%s,%d",ap_info[i].ssid,tmp_ssid);
            arr[tmp_ssid][idx] = rssiVal;
        } 
        else { // unknown AP
            if (rssiVal == 0) { 
                rssiVal = 99;
            }
            arr[unknown_AP_start_pointer][idx] = rssiVal;
            unknown_AP_start_pointer++;
        }
    }
}


// Main Code
void app_main(void) {

    // A - Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK( ret );
    printf("\nPart A Success");
    // B - Initialize Wi-Fi modules
    wifi_init();
    wifi_start();
    
    int ESP_STA_ID;
    if (ESP_STA_CHAR=='L') {
        ESP_STA_ID=1;
    } else {
        ESP_STA_ID=2; 
    }
    printf("\nPart B1 Success\n");
    // C - Select mode (1: 1 AP; 2: Multiple APs; 3: Multiple APs: waypoint following) 
    wifiConnectConfig(); // Set up Wi-Fi Config
    printf("\nPart B2 Success\n");

    char rx_buffer[MAX_BUFFER_SIZE] = {};
    int start_up_sync = 1;
    int8_t raw_data[DEFAULT_SCAN_LIST_SIZE][NUM_READINGS_PER_ITER]; // Initialize array to store 
    char strArr[DEFAULT_SCAN_LIST_SIZE*NUM_READINGS_PER_ITER*3+10] = {"0"}; // 50,50,50,50,|20,20,20,20,|30,30,30,30,

    while (1) {

        // Setup and Connect Wifi
        // Setup and Connect UDP
        // If first time: Send to Laptop: ESP32-1 (or 2) ready. Reset First-time flag
        // Else: Send to Laptop: Data required
        // Loop and wait for Command to Scan
        // Once command received, disconnect from Wifi/UDP and perform Scan 

        // a - Setup Wi-Fi
        vTaskDelay(5000/portTICK_PERIOD_MS); // 5 second delay for initial start-up
        wifiConnect();
        vTaskDelay(2500/portTICK_PERIOD_MS); // 2.5 second delay to allow for connection
        printf("\nWi-Fi: 3 seconds given, Wi-Fi initiated");

        // b - Setup UDP
        printf("\nUDP: Create Socket and transfer data\n");
        int sock = 0;
        struct sockaddr_in remote_addr2, local_addr;

        remote_addr2.sin_addr.s_addr = inet_addr(LAPTOP_IP_ADDR2);
        remote_addr2.sin_family = AF_INET;
        remote_addr2.sin_port = htons(LAPTOP_IP_PORT2);
        local_addr.sin_addr.s_addr = htonl(INADDR_ANY); // inet_addr(ESP32_IP_ADDR) add ESP32 IP address
        local_addr.sin_family = AF_INET; 
        local_addr.sin_port = htons(ESP32_IP_PORT); // add ESP32 Receiving Port

        sock = socket(AF_INET, SOCK_DGRAM, 0); // init
        if (sock<0) {
            printf("Unable to create socket: errno %d\n", errno);
            return;
        }
        printf("Socket created, sending to %s: %d \n", LAPTOP_IP_ADDR2, LAPTOP_IP_PORT2);

        uint8_t res = 0;
        res = bind(sock, (struct sockaddr* ) &local_addr, sizeof(local_addr));
        if (res != 0) {
            printf("Socket binding error %d\n", res);
        } else {
            printf("Socket binded %d\n", res);
        }

        // c - Send Data to Laptop (For first time, different packet)
        int err2 = 0;
        
        while (1){ // keep looping here until it is able to successfully send data to laptop/server host. will not collect data until it can confirm ESPL and R initialized
            if (start_up_sync==1){
                sprintf(&strArr[0],"%c",(char) (ESP_STA_CHAR)); // Only transmit this on the first occurence
                start_up_sync=0;
            } 
            printf("\nREBRO String to Transmit: %s\n",strArr);
            err2 = sendto(sock, strArr, strlen(strArr), 0, (struct sockaddr* )&remote_addr2, sizeof(remote_addr2));
            ESP_LOGI(TAG_UDP,"Err number is: %d\n",err2);
            printf("err: %d \n",err2);
            if (err2 > 0) {
                ESP_LOGI(TAG_UDP, "Successfully transfer data to %s:%u\n", inet_ntoa(remote_addr2.sin_addr), ntohs(remote_addr2.sin_port));
                break; // Exit while loop. 
            }  
            ESP_LOGI(TAG_UDP, "Failed to transfer data to %s:%u. Re-attempt Wi-Fi connection.\n", inet_ntoa(remote_addr2.sin_addr), ntohs(remote_addr2.sin_port));

            // vTaskDelay(100000/portTICK_PERIOD_MS); // TEMP
            wifiDisconnect(); 
            vTaskDelay(1000/portTICK_PERIOD_MS); // 1 second given to disconnect
            wifiConnect(); // 
            vTaskDelay(2500/portTICK_PERIOD_MS); // 2.5 second given to connect again
        }

        bool scanAgain = true; // Reset to True

        // d - Wait for Command to (re)scan.
        while (scanAgain) {
            struct sockaddr_storage source_addr; // Large enough for both IPv4 or IPv6
            socklen_t socklen = sizeof(source_addr);            

            ESP_LOGI(TAG_UDP,"Try to receive data");
            
            vTaskDelay(10000/portTICK_PERIOD_MS); // 10 second delay - This replaces recvfrom() command, and automatically repeats scanning and delivery of data every 10 seconds
            scanAgain = false;

            memset(rx_buffer, 0, sizeof(rx_buffer)); // reset buffer
        }

        // e - Shut-down sock and wifi for next scan                        
        close(sock);
        printf("\nWi-Fi: Disconnect");
        wifiDisconnect(); 
        vTaskDelay(1000/portTICK_PERIOD_MS); // 1 second given to disconnect
        printf("\nWi-Fi: 1 second given, Wi-Fi disconnected");
        printf("\nCommence with Scan ... ");

        // f - Reset arrays and begin scanning
        memset(raw_data, 0, sizeof(raw_data));
        memset(strArr, 0, sizeof(strArr));

        // f1 - Get num_readings_per_iter RSSI readings for each location for 3 APs
        for (int i=0;i<NUM_READINGS_PER_ITER;i++){
            scanReadFypApsAndDisplay(raw_data,i); // Scan for all APs, identify fyp AP, and store RSSI value in raw_data[i]
        } 
        
        // f2 - Convert 2D Array Data (unsigned and abs()) into strArr
        int index=0;
        index += sprintf(&strArr[index],"%c$",(char) (ESP_STA_ID+'0')); // Include the ESPID followed by $ delimiter (add 48 -> get the actual ESP ID)
        for (int i=0;i<DEFAULT_SCAN_LIST_SIZE;i++){
            for (int j=0;j<NUM_READINGS_PER_ITER;j++){
                char c = (char) (fmin(raw_data[i][j],93) + ' '); // Convert to character (Raw number + 33)
                // printf("\n%u",raw_data[i][j]);
                if (j<NUM_READINGS_PER_ITER-1){
                    index += sprintf(&strArr[index],"%c-",c); // Include delimiter to separate characters 
                } else {
                    index += sprintf(&strArr[index],"%c",c); // For the last character -> can move on to include a '#' delimiter  
                }                        
            }
            index += sprintf(&strArr[index],"#"); // Include '#' to separate the sections
        }
        printf("\nString to Transmit: %s\n",strArr);
    }
}