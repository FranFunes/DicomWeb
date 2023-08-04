$(document).ready(function () {

    // Initialize local device
    $.ajax({
        url: "/get_local_device",   
        contentType: "application/json",
        success: function(response) {                    
            // Update local device info
            $("#localAET").text(response.data.ae_title)
            $("#localIP").text(response.data.address)
            $("#localPort").text(response.data.port)   
        },
        error: function(xhr, status, error) {
            // handle error response here
            console.log(xhr.responseText);
        }
        }); 
        
    // Initialize devices table
    var devices_table = $('#devices').DataTable({
        ajax: "/get_devices",
        columns: [            
            { data: 'name', title:'Nombre' },
            { data: 'ae_title', title: 'AE Title' },
            { data: 'address', title: 'Dirección' }
        ],
        searching: false,
        paging: false,
        ordering: false,
        info: false,
        language: {
            "emptyTable": "No peer devices configured"
          }         
    });

    // Enable select behaviour for device table
    $('#devices tbody').on('click', 'tr', function () {                
        if (!$(this).hasClass('selected')) {                  
            devices_table.rows().deselect()
            devices_table.row($(this)).select()
        }
        else {
            devices_table.rows().deselect()
        }
    });
        
    // ------------------ Device manager

    // Local device manager
    $("#editLocalDevice").on('click', function () {    
        // Fill form with local device info
        $('#localDeviceManagerAET').val($("#localAET").text())        
    })

    // Edit local device form submit
    $("#localDeviceManagerForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();      
        var ajax_data = {
            "ae_title":  $('#localDeviceManagerAET').val()
        }
        $.ajax({
            url: "/manage_local_device",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                alert(response.message)
                // Update local device info
                $("#localAET").text(ajax_data.ae_title)
            },
            error: function(xhr, status, error) {
                // handle error response here
                alert(xhr.responseJSON.message);
            }
            });  
    });

    var deviceAction
    // Adapt modal contents depending on selected action
    $("#newDevice").on('click', function () {
        deviceAction = "add"
        // Reset form
        $("#deviceManagerForm")[0].reset()
        $('.modal-title').text('Añadir dispositivo')
        $('#deviceManagerName').prop('disabled', false)
                
    })
    $("#editDevice").on('click', function () {
        deviceAction = "edit"        
        $('.modal-title').text('Editar dispositivo')
        // Fill form with selected device info
        data = devices_table.rows({ selected: true }).data()[0]
        $('#deviceManagerName').prop('disabled',true)
        $('#deviceManagerName').val(data.name)
        $('#deviceManagerAET').val(data.ae_title)
        $('#deviceManagerIP').val(data.address.split(":")[0])
        $('#deviceManagerPort').val(data.address.split(":")[1])
        $('#deviceManagerImgsSeries').val(data.imgs_series)  
        $('#deviceManagerImgsStudy').val(data.imgs_study)     
    })

    // Delete device
    $("#deleteDevice").on('click', function () {

        var ajax_data = devices_table.rows({ selected: true }).data()[0]
        ajax_data.action = "delete"

        $.ajax({
            url: "/manage_devices",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                alert(response.message)
                devices_table.ajax.reload()
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            }); 
    })

    // New/Edit form submit
    $("#deviceManagerForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();        

        var ajax_data = {
            "action": deviceAction,
            "name": $('#deviceManagerName').val(),
            "ae_title":  $('#deviceManagerAET').val(),
            "address": $('#deviceManagerIP').val(),
            "port": $('#deviceManagerPort').val(),
            "imgs_series": $('#deviceManagerImgsSeries').val(),  
            "imgs_study": $('#deviceManagerImgsStudy').val()  
        }

        $.ajax({
            url: "/manage_devices",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                alert(response.message)
                devices_table.ajax.reload()
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });     

    });
    
    // Query for imgs fields
    $(".queryImgsFieldBtn").on('click', function(event) {

        console.log('click')
        event.preventDefault();

        $(".queryImgsFieldBtn").each(function() {
            $(this)[0].innerHTML = `<span class="spinner-border spinner-border-sm"></span>`
            $(this).prop('disabled', true);
        })
        
        var ajax_data = {
            "ae_title":  $('#deviceManagerAET').val(),
            "address": $('#deviceManagerIP').val(),
            "port": $('#deviceManagerPort').val()
        }
        $.ajax({
            url: "/query_imgs_field",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                $(".queryImgsFieldBtn").each(function() {
                    $(this)[0].innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                  </svg>`
                    $(this).prop('disabled', false);
                })
                $('#deviceManagerImgsStudy').val(response.imgs_study)
                $('#deviceManagerImgsSeries').val(response.imgs_series)                     
                
            },
            error: function(xhr, status, error) {
                // handle error response here
                $(".queryImgsFieldBtn").each(function() {
                    $(this)[0].innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                  </svg>`
                    $(this).prop('disabled', false);
                })
                $('#deviceManagerImgsStudy').val("Unknown")
                $('#deviceManagerImgsSeries').val("Unknown") 
            }
            });   
    })

});

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';