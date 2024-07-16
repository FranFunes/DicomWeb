$(document).ready(function () {

    // Initialize local device
    $.ajax({
        url: "/get_local_device",   
        contentType: "application/json",
        success: function(response) {                    
            // Update local device info
            $("#localAET").text(response.data.ae_title)
            $("#localPort").text(response.data.port)   
            $("#localIP").text(response.data.address)
            response.data.addresses.forEach((address) => {
                var select = $("#localDeviceManagerAddress")
                var option = $(`<option>${address}</option>`)
                select.append(option)
            })
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
        
    //////////////////////////// Device manager //////////////////////////////

    // Local device manager
    $("#editLocalDevice").on('click', function () {    
        // Fill form with local device info
        $('#localDeviceManagerAET').val($("#localAET").text())      
        $('#localDeviceManagerPort').val($("#localPort").text())   
        $('#localDeviceManagerAddress').val($("#localIP").text())   
    })

    // Edit local device form submit
    $("#localDeviceManagerForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();      
        var ajax_data = {
            "ae_title":  $('#localDeviceManagerAET').val(),
            "port": parseInt($('#localDeviceManagerPort').val()),
            "address": $("#localDeviceManagerAddress").val(),
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
                $("#localPort").text(ajax_data.port)
                $("#localIP").text(ajax_data.address)
            },
            error: function(xhr, status, error) {
                // handle error response here
                alert(xhr.responseJSON.message);
            }
            });  
    });

    // Test local device
    $("#testLocalDevice").on('click', function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();              
        $.ajax({
            url: "/test_local_device",
            success: function(response) {                    
                // Show success message
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here                
                alert('Fallo');
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

    // Ping remote device
    $("#pingRemoteDevice").on('click', function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();     

        $(this)[0].innerHTML = `<span class="spinner-border spinner-border-sm"></span>`
        $(this).prop('disabled', true);
                
        var ajax_data = {
            "address": $('#deviceManagerIP').val()
        }
        $.ajax({
            url: "/ping_remote_device",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                $("#pingRemoteDevice")[0].innerHTML = 'Success'
                $("#pingRemoteDevice").prop('disabled', false)
                $("#pingRemoteDevice").addClass('btn-success')
                $("#pingRemoteDevice").removeClass('btn-danger')

            },
            error: function(xhr, status, error) {
                // handle error response here
                $("#pingRemoteDevice")[0].innerHTML = 'Failed'
                $("#pingRemoteDevice").prop('disabled', false)
                $("#pingRemoteDevice").addClass('btn-danger')
                $("#pingRemoteDevice").removeClass('btn-success')

            }
        });
    });

    // Echo remote device
    $("#echoRemoteDevice").on('click', function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();     

        $(this)[0].innerHTML = `<span class="spinner-border spinner-border-sm"></span>`
        $(this).prop('disabled', true);
        
        var ajax_data = {
            "ae_title":  $('#deviceManagerAET').val(),
            "address": $('#deviceManagerIP').val(),
            "port": parseInt($('#deviceManagerPort').val()),
        }
        
        $.ajax({
            url: "/echo_remote_device",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                $("#echoRemoteDevice")[0].innerHTML = 'Success'
                $("#echoRemoteDevice").prop('disabled', false)
                $("#echoRemoteDevice").addClass('btn-success')
                $("#echoRemoteDevice").removeClass('btn-danger')
            },
            error: function(xhr, status, error) {
                // handle error response here
                $("#echoRemoteDevice")[0].innerHTML = 'Failed'
                $("#echoRemoteDevice").prop('disabled', false)
                $("#echoRemoteDevice").addClass('btn-danger')
                $("#echoRemoteDevice").removeClass('btn-suc cess')
            }
        });
    });
    
    // Query for imgs fields
    $(".queryImgsFieldBtn").on('click', function(event) {

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

    //////////////////////////// Device manager //////////////////////////////

    // Add new basic filter callback
    $("#newBasicFilterBtn").on('click', function(event) {
        element = createBasicFilter()
        element.insertBefore($(this))
    })

    // Add new advanced filter callback
    $("#newFilterBtn").on('click', function(event) {
        element = createFilter()
        element.insertBefore($(this))
    })

    // Adapt modal contents depending on selected action
    $("#editDeviceFilters").on('click', function () {
                
        // Reset existent filters
        $("#editBasicFiltersForm").find('.basicFilter').remove()
        // Fill form with selected device info
        data = devices_table.rows({ selected: true }).data()[0]
        $('#filteredDevice').text(data.name)
        // Show existent basic filters       
        data.filters.forEach(function(filter) {
            element = createBasicFilter(filter.field, filter.value)
            element.insertBefore($("#newBasicFilterBtn"))
        })

        // Reset existent filters
        $("#filters-advanced").find('.advancedFilter').remove()
        // Fill form with selected device info
        data = devices_table.rows({ selected: true }).data()[0]        
        // Show existent filters       
        data.advanced_filters.forEach(function(conditions) {            
            element = createFilter(conditions)
            element.insertBefore($("#newFilterBtn"))
        })
        
    })

    // Edit filters form submit    
    $("#editBasicFiltersForm").submit(function(event) {
        
        event.preventDefault();    
        
        device = devices_table.rows({ selected: true }).data()[0].name
        
        filters = $(this).find('.basicFilter').map(function(index, item) {

                filter_data = {
                        field: $(item).find('.fieldSelect').val(),
                        value: $(item).find('input').val(),
                    }
                return filter_data
            }
        ).get()
        var ajax_data = {
            "device": device,
            "filters":  filters
        }

        $.ajax({
            url: "/update_device_filters",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                devices_table.ajax.reload()
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });
    });

    $("#editFiltersSubmit").on('click',function(event) {
        
        
        event.preventDefault();    
        
        device = devices_table.rows({ selected: true }).data()[0].name
                
        filters = $('.advancedFilter').toArray().map(function(item) {
            var conditions = $(item).find('input')
            return conditions.toArray().reduce(function(conds, cond) {         
                var value
                var key   
                [key, value] = splitString(cond.value)                
                conds[key] = value
                return conds
            }, {})
        })

        var ajax_data = {
            "device": device,
            "filters":  filters
        }

        $.ajax({
            url: "/update_device_filters_2",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                devices_table.ajax.reload()
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
        });
    });


});

// Add basic filter
function createBasicFilter(field, value) {
    
    var element = $(`<div class="row mb-1 basicFilter">                                        
                        <div class="col-sm-4">                        
                            <select class="form-select form-select-sm fieldSelect">
                                <option value="PatientName">PatientName</option>
                                <option value="PatientID">PatientID</option>
                                <option value="Modality">Modality</option>
                                <option value="SeriesDescription">SeriesDescription</option>
                                <option value="SeriesNumber">SeriesNumber</option>
                            </select>
                        </div>
                        <div class="col">
                            <input type="text" class="form-control form-control-sm" placeholder="Valor"> 
                        </div>                                           
                    </div>`)  

    if (field !== undefined) {
        element.find(`.fieldSelect option[value=${field}]`).prop('selected', true);
        element.find('input').val(value)
    }
    var column = $(`<div class="col-sm-1">
                    </div>`)
    var button = $(`<button class="btn btn-sm btn-danger deleteBasicFilter">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6Z"/>
                            <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1ZM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118ZM2.5 3h11V2h-11v1Z"/>
                        </svg>
                    </button>`)
    button.on('click', function(event) {
        event.preventDefault()
        element.remove()
    })    
    column.append(button)    
    element.prepend(column) 
    
    return element
}

// Add filter
function createFilter(conditions = []) {
    
    var element = $(`<div class="card mb-1 advancedFilter">          
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <span>Criterios de inclusión</span>
                            <div>
                                <button type="button" class="btn btn-success btn-sm">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-plus-circle" viewBox="0 0 16 16">
                                            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/>
                                            <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4"/>
                                    </svg>
                                </button>
                                <button type="button" class="btn btn-danger btn-sm">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash3" viewBox="0 0 16 16">
                                    <path d="M6.5 1h3a.5.5 0 0 1 .5.5v1H6v-1a.5.5 0 0 1 .5-.5M11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3A1.5 1.5 0 0 0 5 1.5v1H1.5a.5.5 0 0 0 0 1h.538l.853 10.66A2 2 0 0 0 4.885 16h6.23a2 2 0 0 0 1.994-1.84l.853-10.66h.538a.5.5 0 0 0 0-1zm1.958 1-.846 10.58a1 1 0 0 1-.997.92h-6.23a1 1 0 0 1-.997-.92L3.042 3.5zm-7.487 1a.5.5 0 0 1 .528.47l.5 8.5a.5.5 0 0 1-.998.06L5 5.03a.5.5 0 0 1 .47-.53Zm5.058 0a.5.5 0 0 1 .47.53l-.5 8.5a.5.5 0 1 1-.998-.06l.5-8.5a.5.5 0 0 1 .528-.47M8 4.5a.5.5 0 0 1 .5.5v8.5a.5.5 0 0 1-1 0V5a.5.5 0 0 1 .5-.5"/>
                                    </svg>
                                </button>
                            </div>
                        </div>       
                        <div class="card-body">   
                            
                        </div>
                    </div>`)  
    
    var button = element.find('.btn-danger')
    button.on('click', function(event) {
        event.preventDefault()
        element.remove()
    })      

    var card_body = element.find('.card-body')
    var button = element.find('.btn-success')
        
    button.on('click', function(event) {
        var rule = createCondition()
        card_body.append(rule)        
    })  

    conditions.forEach(function(condition) {
        var rule = createCondition(condition)
        card_body.append(rule)   
    })

    return element
}

function createCondition(condition){
    var rule = $(`<div class="input-group mb-1">
                    <input type="text" class="form-control form-control-sm" placeholder="Filter contents">                    
                    <button class="btn btn-danger btn-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-circle" viewBox="0 0 16 16">
                            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/>
                            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>
                        </svg>
                    </button>
                </div>`)    
    
    if (condition !== undefined) {
        rule.find('input').val(condition)
    }
    var deleteBtn = rule.find('button')
    deleteBtn.on('click', function(event) {
        rule.remove()
    })   
    return rule
}

function splitString(input) {
    // Regular expression to match '=' or '!='
    const regex = /(=|!=)/;
    
    // Split the string based on the regex
    const parts = input.split(regex);
    
    // If the input matches the regex, the array parts will have three elements:
    // [beforeSeparator, separator, afterSeparator]
    if (parts.length === 3) {
        return [parts[0], parts[1] + parts[2]];
    } else {
        // Handle the case where the input string doesn't match the regex
        // Returning the original string as is in this example
        return [input, ''];
    }
}

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';